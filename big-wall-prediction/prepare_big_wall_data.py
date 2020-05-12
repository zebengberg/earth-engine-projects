"""Clean the dataset calculated by earth engine. Some of the elevation data
contains mistakes; these are manually excised. Scaling the dataset to prepare
it for feeding into an ML model. Building the target values based on the
mountain project dataset.
"""

import pandas as pd
import numpy as np

df = pd.read_csv('data/big_wall_data_steepness_70_height_80m.csv')

# Dropping columns we don't care about.
df = df.drop(columns=['system:index', 'centroid_lith', '.geo'])

# There are "holes" in the elevation dataset found at 'USGS/NED'. These holes
# give the appearance of deep wells within the elevation data. They form regions
# in which the elevation at several pixels is much lower than all of the
# surrounding elevation, and hence give "false positives". Manually removing
# these holds after studying the plot of height vs pixel_count. This removes
# roughly 100 data points.
df = df[(df.height < 2.5 * df.pixel_count + 100) & (df.pixel_count > 7)]

# Values in landsat and geology columns do not need scaling. They are already
# distributed somewhat normally around 0 with standard deviation close to 1. We
# do remove landsat bands with negative values -- around 11 of these.
df = df[(df.B2 > 0) & (df.B4 > 0) & (df.B5 > 0) & (df.B6 > 0) & (df.B7 > 0)]

# Reassigning pixel_count to a ratio.
df.pixel_count /= df.height

# Scaling height so that it is contained between 0 and 1.
df.height /= 1000

# Weighting the "target"-values logarithmically.
df.mp_score = df.mp_score.map(lambda x: 0 if x < 5000 else np.log2(x) / 20)


# We will train the model using cliffs that have both large populations and
# roads nearby.
accessible = (df.road_within_1000m == 1) & (df.population_within_100km > 10000)
inaccessible = df.road_within_3000m == 0

df = df.drop(columns=['road_within_1000m', 'road_within_2000m',
'road_within_3000m', 'road_within_4000m', 'road_within_5000m',
'population_within_30km', 'population_within_100km'])

explored = df[accessible]
unexplored = df[inaccessible]

explored.to_csv('data/explored.csv', header=True, index=False)
unexplored.to_csv('data/unexplored.csv', header=True, index=False)