import ee
import numpy as np

ee.Initialize()

# Split up the western US into small rectangles. Each rectangle is searched for
# big walls. For each big wall found, data is collected. Results are exported
# to google drive. Use small rectangle to split bigger region into batches; this
# avoids error (Too many pixels in region) in calling reduceToVector method.

STEEP_THRESHOLD = 70
HEIGHT_THRESHOLD = 50

# Importing datasets

dem = ee.Image('USGS/NED')
roads = ee.FeatureCollection('TIGER/2016/Roads')
pop = ee.ImageCollection('CIESIN/GPWv411/GPW_Population_Count')
pop = pop.first().select('population_count')
lith = ee.Image('CSP/ERGo/1_0/US/lithology')
landsat = ee.ImageCollection("LANDSAT/LC08/C01/T1")
landsat = landsat.filterDate('2017-01-01', '2019-12-31')
# Get rid of clouds
landsat = ee.Algorithms.Landsat.simpleComposite(collection=landsat, asFloat=True)
# Getting bands that might be useful in geology
landsat = landsat.select('B7', 'B6', 'B2', 'B4', 'B5')




#us = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level0')
#.filter(ee.Filter.eq('country_co', 'US'))

# Build up elevation layers.
steep = ee.Terrain.slope(dem).gt(STEEP_THRESHOLD)
dem_masked = dem.updateMask(steep)
# The image steep has two bands: the first is 0 or 1, second is the elevation
steep = steep.addBands(dem_masked.toInt())

# Calculating heights of each connected region of steep terrain.
cliffs = steep.reduceConnectedComponents(reducer='minMax', maxSize=256)
cliffs = cliffs.select('elevation_max') \
  .subtract(cliffs.select('elevation_min')) \
  .rename('cliffs')

cliffs = cliffs.updateMask(cliffs.gt(HEIGHT_THRESHOLD))



def get_cliffs(rectangle):
  """Search within rectangle at high resolution scale to find cliffs."""
  
  # Getting the geometry and height of all cliffs within the rectangle.
  # Using height as a label for connectedness.
  features = cliffs.reduceToVectors(
    reducer='countEvery',
    geometry=rectangle,
    scale=10,
    geometryType='polygon'  # good choices are 'centroid' and 'polygon'
  )
  # Renaming the 'label' property
  features = features.select(['label', 'count'], ['height', 'count'])
  # Getting data for each cliff geometry.
  features = features.map(lambda f: f.set('pop', get_population(f)))
  features = features.map(lambda f: f.set('road', road_within_distance(f, 3000)))
  features = features.map(lambda f: f.set('lith', get_lithology(f)))
  features = features.map(lambda f: f.set('landsat', get_landsat_data(f)))

  # Now features is a FeatureCollection object. Casting it to a list.
  features = features.toList(10000)  # maximum number of features to get
  return features


def get_population(feature):
  """Count population within 50km of feature."""
  geo = feature.geometry()
  disk = geo.buffer(50000)
  count = pop.reduceRegion(reducer='sum', geometry=disk)
  return ee.Number(count.get('population_count')).toInt()


def get_closest_road(feature):
  """Get distance to closest road within 3km of feature."""
  geo = feature.geometry()
  disk = geo.buffer(3000)
  closeRoads = roads.filterBounds(disk)
  return geo.distance(closeRoads.geometry()).toInt()


def road_within_distance(feature, distance):
  """Determine if there is a road within specified distance of feature"""
  geo = feature.geometry()
  disk = geo.buffer(distance)
  closeRoads = roads.filterBounds(disk)
  return closeRoads.size().gt(0)


def get_lithology(feature):
  """Get lithology histogram for polygon bounding cliff."""
  geo = feature.geometry()
  hist = lith.reduceRegion(reducer='frequencyHistogram', geometry=geo).get('b1')
  hist = ee.Dictionary(hist)
  hist_sum = hist.toArray().reduce(reducer='sum', axes=[0]).get([0])
  return hist.map(lambda key, value: ee.Number(value).divide(hist_sum))


def get_landsat_data(feature):
  """Get landsat8 data for polygon bounding cliff."""
  geo = feature.geometry()
  bands = landsat.reduceRegion(reducer='mean', geometry=geo, scale=10)
  # Including some mysterious "band ratios" which could be useful.
  bands = bands.set('B42', ee.Number(bands.get('B4')).divide(bands.get('B2')))
  bands = bands.set('B65', ee.Number(bands.get('B6')).divide(bands.get('B5')))
  bands = bands.set('B67', ee.Number(bands.get('B6')).divide(bands.get('B7')))
  return bands









# Building an ee.List of rectangles objects.
x0, x1, dx = -125, -102, 0.2
y0, y1, dy = 31, 49, 0.2

# testing stuff instead; delete these later
x0, x1, dx = -107, -106.9, 0.1
y0, y1, dy = 39, 39.1, 0.1


rectangles = [ee.Geometry.Rectangle(x, y, x + dx, y + dy)
              for x in np.arange(x0, x1, dx) for y in np.arange(y0, y1, dx)]

# Casting to an ee.List rather than ee.FeatureCollection, since the get_cliffs()
# function cannot be mapped over ee.FeatureCollection.
rectangles = ee.List(rectangles)

results = rectangles.map(get_cliffs, True)  # dropping nulls
results = results.flatten()
results = results.map(lambda f: ee.Feature(f).get('landsat'))
# results = results.map(lambda f: ee.Feature(f).toArray(['count', 'height', 'pop', 'road']))
print(results.getInfo())



# // Getting just the centroids of each region fo exporting.
# var toExport = results.map(function(feat) {
#   feat = ee.Feature(feat);
#   return feat.centroid(1e-3);
# });

# // Adding centroids as property (not sure if there is a better way).
# // toExport = toExport.map(function(feat) {
# //   feat = ee.Feature(feat);
# //   var geo = feat.geometry().coordinates();
# //   return feat.set({longitude: geo.get(0), latitude: geo.get(1)});
# // });

# // Exporting results to google drive.
# // toExport = ee.FeatureCollection(toExport);  // casting from ee.List
# // Export.table.toDrive({
# //   collection: toExport,
# //   description: 'utah',
# //   fileFormat: 'CSV',
# //   folder: 'earth-engine',
# //   fileNamePrefix: 'utah',
# //   selectors: ['longitude', 'latitude', 'height'],
# // });

