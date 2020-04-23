/*
* This script uses only elevation data to identify connected regions of steep
* terrain. A region is deemed "steep" if it passes two tests: the pixels in
* the region all have slope greater than a given threshold, and the total 
* elevation change within the region is greater than a second given threshold.
* This file finds steep terrain in Utah; the parameters x0, x1, y0, and y1 can
* be modified to find steep terrain in most of the US.
*/

// Two parameters that the user can control.
// Any region of terrain at least as steep as STEEP_THRESHOLD and at least as
// tall as HEIGHT_THRESHOLD is considered a cliff.
var STEEP_THRESHOLD = 75;
var HEIGHT_THRESHOLD = 100;


// US elevation data.
var usdem = ee.Image('USGS/NED');

// Building up map layers.
var steep = ee.Terrain.slope(usdem).gt(STEEP_THRESHOLD);

// Adding elevation data to steep so that we can call reduceConnected... method.
var usdemMasked = usdem.mask(steep);
steep = steep.addBands(usdemMasked);

// Calculating heights of each connected region of steep terrain.
var maxSize = 256;
var heights = steep.reduceConnectedComponents(
  ee.Reducer.minMax(),
  null,
  maxSize
);
heights = heights.select('elevation_max')
.subtract(heights.select('elevation_min'))
.rename('heights');

// Only interested in heights > threshold.
heights = heights.mask(heights.gt(HEIGHT_THRESHOLD));

// Creating a constant image needed to pass to reduceToVectors() method.
var constant = ee.Image(1).mask(heights);
var cliffs = constant.addBands(heights);

// Creating a FeatureCollection of rectangles to analyze.
var x0 = -114;
var x1 = -109;
var y0 = 37;
var y1 = 41;
var dx = 0.2;
var dy = 0.2;
var rectangles = [];
for (var x = x0; x < x1; x += dx) {
  for (var y = y0; y < y1; y += dy) {
    rectangles.push(
      ee.Feature(ee.Geometry.Rectangle(x, y, x + dx, y + dy))
    );
  }
}

// Casting rectangles to an ee.List in order to run server-side map() method.
// Using ee.List rather than ee.FeatureCollection because we want to allow each
// rectangle to generate its own FeatureCollection, which we will then merge.
rectangles = ee.List(rectangles);

// Analyze all rectangles
var results = rectangles.map(analyzeRectangle, true);  // dropping nulls
results = results.flatten();

// Getting just the centroids of each region fo exporting.
var toExport = results.map(function(feat) {
  feat = ee.Feature(feat);
  return feat.centroid(1e-3);
});

// Adding centroids as property (not sure if there is a better way).
toExport = toExport.map(function(feat) {
  feat = ee.Feature(feat);
  var geo = feat.geometry().coordinates();
  return feat.set({longitude: geo.get(0), latitude: geo.get(1)});
});

// Exporting results to google drive.
toExport = ee.FeatureCollection(toExport);  // casting from ee.List
Export.table.toDrive({
  collection: toExport,
  description: 'utah',
  fileFormat: 'CSV',
  folder: 'earth-engine',
  fileNamePrefix: 'utah',
  selectors: ['longitude', 'latitude', 'height'],
});

// Displaying with a big red dot in case toDisplay layer is invisible.
Map.addLayer(toExport.style({pointSize: 10, color: 'red'}), null,
             'cliff big dots', false);

// Give each found cliff a color from custom color palette.
var palette = ee.List(['FFFF00', 'FFF000', 'FFE000', 'FFD000',
  'FFC000', 'FFB000', 'FFA000', 'FF9000', 'FF8000', 'FF7000',
  'FF6000', 'FF5000', 'FF4000', 'FF3000', 'FF2000', 'FF1000',
  'FF0000', 'FF0010', 'FF0020', 'FF0030', 'FF0040', 'FF0050',
  'FF0060', 'FF0070', 'FF0080', 'FF0090', 'FF00A0', 'FF00B0']);
var toDisplay = results.map(function(feat) {
  feat = ee.Feature(feat);
  // Getting the index within the palette list to color the feature.
  var index = ee.Number(feat.get('height')).divide(40).floor();
  return feat.set({style: {color: palette.get(index)}});
});

// Displaying results on map.
toDisplay = ee.FeatureCollection(toDisplay);  // casting from ee.List
// The .style(...) converts the vector object to a raster object.
Map.addLayer(toDisplay.style({styleProperty: 'style'}), null, 'cliff vector');


// Search within rectangle at specified scale find cliffs.
function analyzeRectangle(rectangle) {
  // Need to explicitly tell ee what object is contained in the list rectangles.
  rectangle = ee.Feature(rectangle);
  
  // Getting the geometry and height of all cliffs within the rectangle.
  // Using height as a label for connectedness.
  var features = cliffs.reduceToVectors({
    reducer: ee.Reducer.mode(),  // taking mode of lithology layer
    geometry: rectangle.geometry(),
    scale: 10,
    geometryType: 'polygon',  // good choices are 'centroid' and 'polygon'
  });
  
  features = features.select(['mode'], ['height']);

  // Casting to a list so that we can later flatten it.
  features = features.toList(1000);  // getting at most 1000 cliffs per rectangle

  // If no cliffs found, return null. Will then be dropped from results list.
  return ee.Algorithms.If(features.size(), features, null);
}

// Useful to add raster layer to make sure reduceToVectors() method is working.
// Also useful to get the numeric height reading of a cliff.
Map.addLayer(
  heights.select('heights'),
  {min: HEIGHT_THRESHOLD, max: 500, palette: ['yellow', 'red']},
  'cliff raster', false
);

// Adding elevation data for exploration.
Map.addLayer(usdem, null, 'elevation', false);

