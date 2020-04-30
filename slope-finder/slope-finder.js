/*
 * IMPORT DATA
 */

// The main datasets for US elevation data are SRTM and NED. The NED dataset
// has a higher resolution.
var dem = ee.Image('USGS/NED');
var glcf = ee.ImageCollection("GLCF/GLS_TCC");

// Adding all of the base map stuff.
var map = ui.Map();
map.setOptions('terrain');
map.style().set({cursor: 'crosshair'});
ui.root.widgets().reset([map]);


/*
 * BUILD SIDE PANEL
 */

// Adding title and descriptions.
var sidePanel = ui.Panel(null, null, {width: '300px'});
ui.root.widgets().add(sidePanel);

sidePanel.add(ui.Label(
  'Slope Finder',
  {fontSize: '36px', fontWeight: 'bold', textAlign: 'center', width: '250px'}
));

sidePanel.add(ui.Label(
  'Analyze GIS data to find backcountry ski zones. Zoom in to get started.',
  {fontWeight: 'bold', margin: '20px'}
));

sidePanel.add(ui.Label(
  'Choose the aspect and slope angle you hope to ski...',
  {margin: '10px'}
));


// Adding sliders and checkboxes for user to provide input.
var aspectSlider = ui.Slider({
  max: 350,
  step: 10,
  onChange: buildTarget,
  style: {width: '155px', fontWeight: 'bold'}
});

var aspectLabel = ui.Label(
  'Aspect, measured in degrees',
  {width: '120px'}
);

sidePanel.add(
  ui.Panel([aspectLabel, aspectSlider],
  ui.Panel.Layout.Flow('horizontal')
));


var slopeSlider = ui.Slider({
  max: 60,
  value: 20,
  step: 2,
  onChange: buildTarget,
  style: {width: '155px', fontWeight: 'bold'}
});

var slopeLabel = ui.Label(
  'Slope angle, measured in degrees',
  {width: '120px'}
);

sidePanel.add(
  ui.Panel([slopeLabel, slopeSlider],
  ui.Panel.Layout.Flow('horizontal')
));


var treeCheck = ui.Checkbox({
  onChange: function(value) {
    treeSlider.setDisabled(!value);
    buildTree();
  }});
  
var treeLabel = ui.Label(
  'Mask heavily forested areas with white?'
);

sidePanel.add(
  ui.Panel([treeLabel, treeCheck],
  ui.Panel.Layout.Flow('horizontal')
));


var treeSlider = ui.Slider({
  max: 100,
  step: 10,
  value: 50,
  onChange: buildTree,
  disabled: true,
  style: {width: '155px', fontWeight: 'bold'}
});

var treeSlideLabel = ui.Label(
  'Threshold for masking forest data. Forest data is very inaccurate!',
  {width: '120px'}
);

sidePanel.add(
  ui.Panel([treeSlideLabel, treeSlider],
  ui.Panel.Layout.Flow('horizontal')
));


var ridgeCheck = ui.Checkbox({
  label: 'Ridges',
  onChange: buildRidges,
  style: {color: 'blue', fontWeight: 'bold'}
});

var drainageCheck = ui.Checkbox({
  label: 'Drainages',
  onChange: buildDrainages,
  style: {color: 'purple', fontWeight: 'bold'}
});

var ridgeLabel = ui.Label(
  'Display possible ridge lines and/or drainages? This only looks '
  +' reasonable when zoomed way in!',
  {width: '150px'}
);

sidePanel.add(
  ui.Panel([ridgeLabel, ui.Panel([ridgeCheck, drainageCheck])],
  ui.Panel.Layout.Flow('horizontal')
));


var legendCheck = ui.Checkbox({onChange: buildLegend});

var legendLabel = ui.Label('Display color legend?');

sidePanel.add(
  ui.Panel([legendLabel, legendCheck],
  ui.Panel.Layout.Flow('horizontal')
));


var NUM_STEPS = 100;  // Initial value
var stepSlider = ui.Slider({
  min:  20,
  max: 500,
  step: 20,
  value: NUM_STEPS,
  onChange: function(value) {
    NUM_STEPS = value;
    clearResults();
  },
  style: {width: '155px', fontWeight: 'bold'}
});

var stepLabel = ui.Label(
  'Number of steps used in calculating gradient descent. More steps '
  + 'require more calculation! Changing this will reset results.',
  {width: '120px'}
);

sidePanel.add(
  ui.Panel([stepLabel, stepSlider],
  ui.Panel.Layout.Flow('horizontal')
));


/*
 * BUILD RESULTS PANEL
 */

var resultsPanel = ui.Panel({style: {position: 'bottom-left', width: '500px'}});
map.add(resultsPanel);
clearResults();


/*
 * DEFINE MAP LAYERS
 */

// Adding terrain bands including slope and aspect.
dem = ee.Terrain.products(dem);

// Getting and smoothing a slope layer. Smoothing with an aggresive kernel
// (large radius) to give a smooth path during gradient descent.
var slopeLayer = dem.select('slope')
.convolve(ee.Kernel.circle({radius: 8}))
.rename('slope');

// Getting the aspect layer, measured in degrees.
// Note: It does not make any sense to smooth this aspect layer via
// convolution! Aspect takes values between 0 and 359, though mathematically
// the value lives on a circle. If say 1 and 359 are averaged, the result is
// 180, whereas the "correct" average on the circle is 0.
var aspectLayer = dem.select('aspect')

// Grabbing sine and cosine values from aspectLayer, and smoothing
// them (see note above). Useful for gradient descent.
var sinLayer = aspectLayer.multiply(Math.PI / 180).sin().rename('sinLayer');
var cosLayer = aspectLayer.multiply(Math.PI / 180).cos().rename('cosLayer');
// If we smooth too much (radius too large), then gradient descent path
// ignores smaller features like ridges, hopping over them.
sinLayer = sinLayer.convolve(ee.Kernel.circle({radius: 4}));
cosLayer = cosLayer.convolve(ee.Kernel.circle({radius: 4}));

// Getting a tree cover layer. The filtered image collection has a few
// distinct images from different parts of the country. We take the max.
var treeLayer = glcf.filter(ee.Filter.date('2010-01-01', '2010-12-31'))
.select('tree_canopy_cover')
.max()
.convolve(ee.Kernel.gaussian(5, 3))
.rename('tree');


// Looking for ridges and drainages based on extreme values of the
// laplacian of the elevation surface. Smoothing both before and after
// laplacian is calculated.
var laplacian = dem.select('elevation')
.convolve(ee.Kernel.gaussian(5, 3))
.convolve(ee.Kernel.laplacian8())
.convolve(ee.Kernel.gaussian(5, 3));
var ridgeLayer = laplacian.lt(-1).selfMask();
var drainageLayer = laplacian.gt(1).selfMask();


/*
 * DEFINE CALLBACK FUNCTIONS
 */


// Calculate and render the target layer on the map.
function buildTarget() {
  // Setting arbitrary lower elevation threshold for target regions.
  var LOWER_ELEVATION_THRESHOLD = 7000;  // unit is feet
  var target = dem.select('elevation')
  .gt(LOWER_ELEVATION_THRESHOLD / 3.28084)
  .rename('target');

  // Getting terrain within +- 10 degrees of user's target slope angle.
  var TARGET_SLOPE = ee.Number(slopeSlider.getValue());
  var LOWER_SLOPE = TARGET_SLOPE.subtract(10);
  var UPPER_SLOPE = TARGET_SLOPE.add(10);
  target = target.and(
    slopeLayer.gt(LOWER_SLOPE).and(slopeLayer.lt(UPPER_SLOPE))
  );
  
  // Getting terrain within approximately +-45 degrees of user target aspect.
  var TARGET_ASPECT = ee.Number(aspectSlider.getValue());
  // Dealing with discontinuities of aspect values by taking cosine.
  // See commented note where aspectLayer is defined.
  target = target.and(
    aspectLayer.subtract(TARGET_ASPECT).multiply(Math.PI / 180).cos().gt(0.7)
  );

  // Masking and scaling target according to slope.
  target = target.selfMask();
  target = target.multiply(slopeLayer);
  
  // Replacing any old target layer with the one just built.
  map.layers().forEach(function(layer) {
    if (layer.get('name') === 'target') {
      map.layers().remove(layer);
    }
  });
  map.addLayer(
    target,
    {min: 20, max: 40, palette: ['green', 'yellow', 'red'], opacity: 0.5},
    'target'
  );
}

// Render target layer once when app is launched.
buildTarget();


// Add or remove legend from the map.
function buildLegend(value) {
  if (value) {
    var bar = ui.Thumbnail({
      image: ee.Image.pixelLonLat().select(1),
      params: {
        bbox: [0, 20, 1, 40],
        dimensions: '20x400',
        format: 'png',
        min: 20,
        max: 40,
        palette: ['green', 'yellow', 'red'],
      },
      style: {stretch: 'vertical', margin: '8px 0px'},
    });

    var legendLabel = ui.Panel([
        ui.Label(40, {margin: '4px 8px', fontWeight: 'bold', height: '20px'}),
        ui.Label(30, {margin: '4px 8px', fontWeight: 'bold', height: '400px'}),
        ui.Label(20, {margin: '4px 8px', fontWeight: 'bold', height: '20px'})
      ]);
      
    var legend = ui.Panel([
      ui.Label('Slope', {fontWeight: 'bold', margin: '2px'}),
      ui.Label('Angle', {fontWeight: 'bold', margin: '2px'})]
    );
    
    legend.add(ui.Panel(
      [bar, legendLabel],
      ui.Panel.Layout.flow('horizontal')
    ));
    
    legend.style().set({position: 'bottom-right'});

    map.add(legend);
    
  } else {
    map.remove(map.widgets().get(1));
  }
}


// Add or remove tree layer from the map.
function buildTree() {
  // Removing any exiting tree layer.
  map.layers().forEach(function(layer, _) {
      if (layer.get('name') === 'tree') {
        map.layers().remove(layer);
      }
    });
  
  // Adding a new tree layer if asked to do so.
  if (treeCheck.getValue()) {
    map.addLayer(
      treeLayer.gt(treeSlider.getValue()).selfMask(),
      {opacity: 0.6, palette: 'white'},
      'tree'
    );
  }
}


// Add or remove ridge layer from the map. Calculated with laplacian.
function buildRidges(value) {
  if (value) {
    map.addLayer(ridgeLayer, {palette: 'blue', opacity: 0.5}, 'ridges');
  } else {
    map.layers().forEach(function(layer) {
      if (layer.get('name') === 'ridges') {
        map.layers().remove(layer);
      }
    });
  }
}

// Add or remove drainage layer from the map. Calculated with laplacian.
function buildDrainages(value) {
  if (value) {
    map.addLayer(drainageLayer, {palette: 'purple', opacity: 0.5}, 'drainages');
  } else {
    map.layers().forEach(function(layer) {
      if (layer.get('name') === 'drainages') {
        map.layers().remove(layer);
      }
    });
  }
}


/*
 * PERFORM GRADIENT DESCENT
 */

// Calculate and track data from gradient descent. This function is a callback
// attached to the map.
function gradDescent(coords) {
  // Showing user that their click has been registered.
  var calculatingLabel1 = ui.Label('Calculating....', {color: 'red'});
  if (dataCount === 0) {
    var calculatingLabel2 = ui.Label('You can continue to generate additional '
    + 'paths in the meantime.');
    resultsPanel.clear().add(calculatingLabel1).add(calculatingLabel2);
  } else {
    // If Calculating.... label not present, add it.
    if (resultsPanel.widgets().length() === 3) {
      resultsPanel.add(calculatingLabel1);
    }
  }
  
  // Updating the client-side count of paths.
  dataCount++;
  

  // Function to be passed to ee.List.iterate(...) method. This function is
  // actually doing the step by step data collection.
  var gradStep = function(current, previous) {
    previous = ee.Dictionary(previous);

    var x0 = ee.Number(ee.List(previous.get('path')).get(-2));
    var y0 = ee.Number(ee.List(previous.get('path')).get(-1));
    var p0 = ee.Geometry.Point(x0, y0);
    
    // Grabbing local data at the current location p0.
    var red = ee.Reducer.first();  // reducer repeatedly called
    var local = dem.reduceRegion(red, p0);
    var localSin = ee.Number(sinLayer.reduceRegion(red, p0).get('sinLayer'));
    var localCos = ee.Number(cosLayer.reduceRegion(red, p0).get('cosLayer'));
    var localSlope = ee.Number(slopeLayer.reduceRegion(red, p0).get('slope'));
    var localElevation = ee.Number(local.get('elevation')).multiply(3.28084);

    // Taking a step in direction of gradient.
    var STEP_SIZE = 0.0002;  // constant; could be a slider-value
    var x1 = x0.add(localSin.multiply(STEP_SIZE));
    var y1 = y0.add(localCos.multiply(STEP_SIZE));

    // Updating and returning the data.
    return ee.Dictionary({
      path: ee.List(previous.get('path')).cat(ee.List([x1, y1])),
      elevation: ee.List(previous.get('elevation')).add(localElevation),
      slope: ee.List(previous.get('slope')).add(localSlope),
    });
  };

  // Client-side list of colors to distinguish drawn gradient descent paths.
  var distinctiveColors = [
    'red',
    'cyan',
    'lime',
    'orange',
    'yellow',
    'deeppink',
    'blue',
    'chocolate',
    'fuchsia',
    'teal'
  ];

  // Performing grad descent with server-side ee.List.iterate(...). Here
  // numIteration is simply a placeholder; gradStep doesn't do anything to it.
  var numIteration = ee.List.sequence(1, NUM_STEPS);

  // A dictionary containing data gathered over gradient descent.
  // This variable is the starting value for the iterate(...) method.
  var data = ee.Dictionary({
    path: ee.List([coords.lon, coords.lat]),
    elevation: [],
    slope: [],
  });


  // Doing the iteration. This is the slow step.
  data = ee.Dictionary(numIteration.iterate(gradStep, data));

  // Getting a color and title for the gradient descent path.
  var color = distinctiveColors[dataCount % 10];
  var title = 'path' + dataCount;

  // Attaching callback to data; the chart is built after data is calculated.
  data.evaluate(function(returned) {
    updateChart(returned, title, color);
  });

  // Adding path generated from the iteration to the map.
  var path = ee.Geometry.LineString(data.get('path'));
  map.addLayer(path, {color: color}, title);
}

// Attaching gradDescent as a callback to the map
map.onClick(gradDescent);


/*
 * BUILD CHART
 */


// Build DataTable literal to pass to google charts API. This function
// retrieves server-side data and performs client-side operations in order
// to build native js object. Search DataTable literal for more information.
function buildDataTable(data) {
  // Asking server for string representation of data from gradient descent.
  var jsdata = ee.Serializer.toReadableJSON(data);
  jsdata = JSON.parse(jsdata);  // parsing the string to json

  // Filling the dataTable; not pretty.
  var dataTable = {
    cols: [{type: 'number'}],
    rows: []
  };
  
  // Can't use ES6 tools
  for (var j = 0; j < NUM_STEPS; j++) {
    dataTable.rows.push({c: [{v: j}]});
  }

  for (var i = 0; i < jsdata.length; i++) {
    var dict = jsdata[i];
    dataTable.cols.push({type: 'number'});
    dataTable.cols.push({type: 'number', role: 'tooltip'});
    
    for (j = 0; j < NUM_STEPS; j++) {
      dataTable.rows[j].c.push({v: jsdata[i].value.elevation[j]});
      dataTable.rows[j].c.push({v: jsdata[i].value.slope[j]});
    }
  }
  
  return dataTable;
}


// Updates the chart to include data from gradient descent. This function is
// attached to a list as a callback from within gradDescent().
function updateChart(data, title, color) {
  // Sometimes this callback gets called twice. The second call passes data
  // as undefined. In this case, we force an early exit.
  if (data === undefined) { return null; }
  
  // Updating client-side storage containers.
  dataList.push(data);
  colors.push(color);
  titles.push(title);
  titles.push(title + ' slope');

  // Building the chart from dataTable literal.
  var dataTable = buildDataTable(dataList);
  var chart = ui.Chart(dataTable)  
  .setSeriesNames(titles)
  .setOptions({
    title: 'Elevation profile',
    hAxis: {title: 'Number of gradient descent steps'},
    vAxis: {title: 'Elevation (feet)'},
    colors: colors,
    pointSize: 0,
    lineWidth: 3,
  });

  // Displaying chart on the results panel.
  var button = ui.Button('Clear results', clearResults);
  var description = ui.Label('Hover over curves to view slope. Press arrow '
  + ' in corner to open enlarged chart in new tab.');
  resultsPanel.clear().add(chart).add(description).add(button);
}



// A client-side counter which we can plug into if statements and use to name
// paths calculated during gradient descent.
var dataCount = 0;

// Containers to store data coming from gradient descent. All are client-side
// native js arrays and mutable.
var dataList = [];
var colors = [];
var titles = [];


// Clears client-side storage containers and the result panel.
function clearResults() {
  // Removing all existing paths from map. Going in reverse so we don't skip
  // over a layer after one is removed.
  for (var i = map.layers().length() - 1; i >= 0; i--) {
    var layer = map.layers().get(i);
    if (layer.get('name').slice(0, 4) === 'path') {
      map.layers().remove(layer);
    }
  }

  // Resetting global client-side variables.
  dataCount = 0;
  dataList = [];
  colors = [];
  titles = [];
  
  // Resetting panel.
  var instructionsLabel = ui.Label(
    'Click map to generate a "fall line" path to analyze. You' 
    + ' can generate additional paths while one is loading.'
    + ' These get calculated slowly....');
  resultsPanel.clear().add(instructionsLabel);
}