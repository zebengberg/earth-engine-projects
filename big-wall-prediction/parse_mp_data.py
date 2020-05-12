"""Parse data collected with mountain-project-scraper.
See https://github.com/alexcrist/mountain-project-scraper."""

import json
import pandas as pd
import random
from collections import defaultdict

# Loading data scraped.
with open('mountain-project-scraper/clean-data.json') as file:
  data = json.load(file)

# data is a list; converting it to a dict to match format of children
root = {'name': 'All Climbing', 'children': data}

# Notes on the data tree:
#   - Each node in the data tree is either an area or a route.
#   - Each area node has a list (possibly empty) of children.
#   - Each child could be its own area node or a route.
#   - Siblings cannot be mixed types: they are either all routes or all sub-areas.
#   - Each area has a lat / long. These are inherited from parent in many cases.
#   - Routes do not have lat / long.


def print_random_branch():
  """Print a random branch from the data tree."""
  node = root
  depth = 0
  while 'children' in node and node['children']:
    print(' ' * depth + node['name'])
    depth += 1
    node = random.choice(node['children'])
  else:
    print(' ' * depth + node['name'])
    for key in node:
      print(' ' * depth, key, node[key])


# Counting number of routes according to their types. Types of routes include:
# 'tr', 'trad', 'sport', 'boulder', 'aid', 'mixed', 'ice', 'alpine', and 'snow'.
# We store data in defaultdicts using the coordinates as keys. We aggregate MP
# route types into the three distinct types below.
boulder_dict = defaultdict(int)
winter_dict = defaultdict(int)
rock_dict = defaultdict(int)
# Used to count total number of page views.
views_dict = defaultdict(int)


def dfs(node):
  """Populate route_types_dict with DFS."""

  # Sometimes node has 'children' property, but it is an empty list. This
  # if-statement avoids this situation.
  if node['children']:
    # If one child is not a leaf, then no child is a leaf.
    if 'children' in node['children'][0]:
      for child in node['children']:
        dfs(child)

    # All children are leaf nodes, ie, routes!
    else:
      # Using parent coordinates as dictionary key
      key = (node['lat'], node['long'])
      for child in node['children']:
        if 'types' in child:
          types = child['types']
          if 'boulder' in types:
            boulder_dict[key] += 1
          elif 'mixed' in types or 'ice' in types or 'snow' in types:
            winter_dict[key] += 1
          else:
            rock_dict[key] += 1
        if 'totalViews' in child:
          views_dict[key] += child['totalViews']


dfs(root)


# Rarely is a key shared by all three dictionaries; taking the union here so we
# can iterate over it to build pandas DataFrame.
keys = set(boulder_dict.keys()).union(
  set(winter_dict.keys())).union(set(rock_dict.keys()))

# A list of dictionaries to be passed to a pandas DataFrame.
pre_df = []
for key in keys:
  d = {
    'latitude': key[0],
    'longitude': key[1],
    'num_boulders': boulder_dict[key],
    'num_rock_routes': rock_dict[key],
    'num_winter_routes': winter_dict[key],
    'num_views': views_dict[key],
    }
  pre_df.append(d)

# Exporting data.
df = pd.DataFrame(pre_df)
df.to_csv('data/mp_data.csv', header=True, index=False)
