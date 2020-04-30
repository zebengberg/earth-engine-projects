import ee

ee.Initialize()

# Defining elevation data.
dem = ee.Image('USGS/NED')
# Coordinates of mountain summit and a rectangle enclosing containing mountain
# contours under consideration.
rect = ee.Geometry.Rectangle(-110.93, 36.98, -110.81, 37.08)
summit = ee.Geometry.Point(-110.869, 37.035)

# Clipping and smoothing elevation layer.
dem = dem.clip(rect)
dem = dem.convolve(ee.Kernel.gaussian(5, 4))

# An ee.List containing contour elevations to calculate. Get errors if the
# elevations are too close to summit elevation.
lines = ee.List.sequence(1800, 3100, 10)

# An ee.List of masked ee.Images.
contours = lines.map(lambda l: dem.gt(ee.Number(l)).selfMask().set({'ele': l}))


def convert_to_polygon(c):
    """Convert contour image to polygon containing summit."""
    c = ee.Image(c).toInt()
    ele = c.get('ele')
    features = c.reduceToVectors(scale=10)

    # Only keeping contour line containing the summit.
    features = features.filterBounds(summit)

    # Features in now a singleton FeatureCollection; grabbing the only element.
    # This can be a null object if contours are too close to summit elevation.
    feature = ee.Feature(features.first())

    # Keeping the elevation property.
    feature = feature.set({'elevation': ele})
    return feature.select(['elevation'])


# Converting contours to a vector object. After calling ee.reduceToVectors(),
# each contour is either a Polygon or MultiPolygon object. For MultiPolygon
# objects, we only keep the polygon containing the summit.
contours_as_polygons = contours.map(convert_to_polygon)


def perimeter_at_scale(vertices, scale):
    """Calculate the average perimeter of the sub-polygons obtained by sampling
     vertices at specified scale."""

    # A scale of 10 indicates that we look at  the sub-polygon obtained by
    # keeping every 10th vertex of the original polygon. By changing the
    # starting point, there are 10 such polygons. We consider all 10, and
    # average their perimeters.
    scale = ee.Number(scale)
    shifts = ee.List.sequence(0, scale.subtract(1))

    def get_perimeter(start):
        """A callback function that calculates the perimeter of a sub-poly."""
        end = vertices.length().subtract(1)
        sub_vertices = ee.List.sequence(start, end, scale)
        sub_vertices = sub_vertices.map(lambda n: vertices.get(n))
        poly = ee.Geometry.Polygon(sub_vertices)
        return poly.perimeter()

    perimeters = shifts.map(get_perimeter)

    # Returning the average.
    return ee.Number(perimeters.reduce(ee.Reducer.sum())).divide(scale)


def fractal_dimension(vertices):
    """Calculate the fractal dimension of a polygon by taking a linear
     regression of perimeters at different scaling levels."""

    # Need each list of sub-vertices to have at least three vertices. This gives
    # the inequality length > 3 * stepSize. Now take log base 2 of both sides to
    # get the upper bound on the exponent.
    exponent_bound = vertices.length().log().divide(ee.Number(2).log()) \
        .subtract(ee.Number(3).log().divide(ee.Number(2).log())) \
        .toInt()

    # We start with exponent at 1, which means the perimeter at the most zoomed
    # in resolution will only include every other vertex. We ignore exponent 0
    # because the data is skewed by the discrete dem pixels at this level. At
    # exponent 0 we experience a taxicab-like distance function.
    exponents = ee.List.sequence(1, exponent_bound)
    scales = exponents.map(lambda exp: ee.Number(2).pow(ee.Number(exp)))
    perimeters = scales.map(lambda scale: perimeter_at_scale(vertices, scale))
    log_perimeters = perimeters.map(lambda p: ee.Number(p).log())

    # Fitting a linear model to the log-log data.
    exponents = exponents.reverse()
    inputs = exponents.zip(log_perimeters)
    slope = ee.Dictionary(inputs.reduce(ee.Reducer.linearFit())).get('scale')

    # Returning 1 + slope, which is a measure of fractal dimension.
    return ee.Number(slope).add(ee.Number(1))


def get_stats(poly):
    """Get area, perimeter, and fractal dimension of polygon."""

    poly = ee.Feature(poly)
    # Sometimes poly is actually a MultiPolygon geometry. In this case, we just
    # take the first polygon within it.
    vertices = ee.Algorithms.If(
        poly.geometry().type().compareTo(ee.String('MultiPolygon')),
        poly.geometry().coordinates().get(0),
        ee.List(poly.geometry().coordinates().get(0)).get(0)
    )
    vertices = ee.List(vertices)

    # Calculating perimeter at second-most zoomed-in level to avoid pixel
    # noise. See comment within fractal_dimension definition.
    perimeter = perimeter_at_scale(vertices, 2)

    # Calculating area here rather than at Feature level. This ensures
    # consistency in case that poly was MultiPolygon.
    area = ee.Geometry.Polygon(vertices).area()

    stats_dict = {'elevation': ee.Number(poly.get('elevation')).toInt(),
                  'area': area.toInt(),
                  'perimeter': perimeter.toInt(),
                  'fractal_dim': fractal_dimension(vertices)}

    # Ignoring geometry for export.
    return ee.Feature(None, stats_dict)


# Aggregating some interesting statistics into a FeatureCollection in order to
# use ee.Export.
table = ee.FeatureCollection(contours_as_polygons.map(get_stats))

# Exporting to google drive.
task = ee.batch.Export.table.toDrive(collection=table,
                                     description='contour data',
                                     folder='earth-engine',
                                     fileNamePrefix='navajo',
                                     fileFormat='CSV')

task.start()
print('Current status:', task.status())
# Use ee.batch.Task.list() to see current status of exports.
