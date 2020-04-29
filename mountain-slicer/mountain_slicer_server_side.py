#!/usr/bin/env python
"""Where operator example.
Select the forest classes from the MODIS land cover image and intersect them
with elevations above 1000m.
"""

import ee
from time import sleep


ee.Initialize()

dem = ee.Image('USGS/NED')
rect = ee.Geometry.Rectangle(-110.93, 36.98, -110.81, 37.08)
summit = ee.Geometry.Point(-110.869, 37.035)

# Clipping and smoothing elevation layer
dem = dem.clip(rect)
dem = dem.convolve(ee.Kernel.gaussian(5, 4))

# An ee.List containing contour elevations to calculate.
lines = ee.List.sequence(2000, 3100, 100)

# An ee.List of masked ee.Image.
contours = lines.map(lambda l: dem.gt(ee.Number(l)).selfMask().set({'ele': l}))


def convert_to_polygon(c):
    """Convert contour image to polygon containing summit."""
    c = ee.Image(c).toInt()
    ele = c.get('ele')
    features = c.reduceToVectors(scale=10)
    # Only keeping contour line containing the summit
    features = features.filterBounds(summit)
    # Features in now a singleton FeatureCollection; grabbing the only element.
    feature = ee.Feature(features.first())
    feature = feature.set({'elevation': ele, 'area': feature.area(1).toInt()})
    return feature.select(['elevation', 'area'])


# Converting contours to a vector object. After calling ee.reduceToVectors(),
# each contour is either a Polygon or MultiPolygon object. For MultiPolygon
# objects, we only keep the polygon containing the origin.
contours_as_polygons = contours.map(convert_to_polygon)


def perimeter_at_scale(vertices, step_size):
    """Calculate the average perimeter of the sub-polygons obtained by sampling
     vertices at specified steps."""

    shifts = ee.List.sequence(0, step_size - 1)

    def get_perimeter(start):
        end = vertices.length().subtract(1)
        sub_vertices = ee.List.sequence(start, end, step_size)
        sub_vertices = sub_vertices.map(lambda n: vertices.get(n))
        poly = ee.Geometry.Polygon(sub_vertices)
        return poly.perimeter()

    perimeters = shifts.map(get_perimeter)
    # Returning the average.
    return ee.Number(perimeters.reduce(ee.Reducer.sum())).divide(step_size)


poly = ee.FeatureCollection(contours_as_polygons.get(5));
poly = ee.Feature(poly)
vertices = ee.List(poly.geometry().coordinates().get(0))
print(perimeter_at_scale(vertices, 700).getInfo())


def get_stats(p):
    """Get area and perimeter of polygon p."""
    p = ee.Feature(p)
    return ee.Feature(None,
                      {'elevation': p.get('elevation'),
                       'perimeter': p.perimeter(1).toInt(),  # error threshold
                       'area': p.area(1).toInt()
                       })


# Aggregating some interesting statistics into a FeatureCollection in order to
# use ee.Export.
# table = ee.FeatureCollection(contour_polygons.map(get_stats))
#
#
# task = ee.batch.Export.table.toDrive(collection=table,
#                                      description='contour data',
#                                      folder='earth-engine',
#                                      fileNamePrefix='navajo',
#                                      fileFormat='CSV')
#
# task.start()
# print(task.status())
# print(task.id)
# Use ee.batch.Task.list() to see current status of exports.



#import pandas as pd
#import matplotlib.pyplot as plt
# data = {'elevation': lines.getInfo(),
#         'area': areas.getInfo(),
#         'perimeter': perimeters.getInfo()}
#
#
# data = pd.DataFrame.from_dict(data)
#
# data.plot(x='elevation', y='perimeter', kind='scatter')
# plt.show()
#
# # TODO: Perhaps use ee.Export rather than getInfo()
# # getInfo() runs into server side issues with too many calls
# # Export may avoid these.