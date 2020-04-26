#!/usr/bin/env python
"""Where operator example.
Select the forest classes from the MODIS land cover image and intersect them
with elevations above 1000m.
"""

import ee
import numpy as np

ee.Initialize()

dem = ee.Image('USGS/NED')
rect = ee.Geometry.Rectangle(-110.93, 36.98, -110.81, 37.08)
summit = ee.Geometry.Point(-110.869, 37.035)

# Clipping and smoothing elevation layer
dem = dem.clip(rect)
dem = dem.convolve(ee.Kernel.gaussian(5, 4))

# An ee.List containing contour elevations to calculate.
lines = ee.List.sequence(2000, 3100, 20)

# An ee.List of masked ee.Image.
contours = lines.map(lambda l: dem.gt(ee.Number(l)).selfMask())


# Converting contours to a vector object. After calling ee.reduceToVectors(),
# each contour is either a Polygon or MultiPolygon object. For MultiPolygon
# objects, we only keep the polygon containing the origin.
def convert_to_polygon(c):
    c = ee.Image(c).toInt()
    features = c.reduceToVectors(scale=10)
    geos = features.geometry().geometries()
    contains_summit = geos.map(lambda p: ee.Geometry(p).contains(summit))
    return geos.get(contains_summit.indexOf(True))

contour_polygons = contours.map(convert_to_polygon)


# Setting error threshold to 1.
perimeters = contour_polygons.map(lambda p: ee.Geometry(p).perimeter(1))
areas = contour_polygons.map(lambda p: ee.Geometry(p).area(1))

print(areas.getInfo())
print(perimeters.getInfo())