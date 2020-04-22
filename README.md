# earth-engine-projects

> A collection of Google Earth Engine scripts.

## Introduction

Google Earth Engine is a tool for exploring and visualizing GIS data. The [API](https://developers.google.com/earth-engine/getstarted) provides a library and framework for running calculations on Google cloud servers. Code in this repository contains a mixture of server-side and client-side operations.

## slope-finder

[This live web app](https://zebengberg.users.earthengine.app/view/slope-finder) uses elevation and forest data to identify promising backcountry ski terrain. User input in the form of target slope angle, aspect, and tree coverage are used to generate map layers showcasing regions of interest. Users can click on the map to generate a path of gradient descent and to visualize path statistics.

## big-wall-finder

[This script](/big-wall-finder/big-wall-finder.js) uses elevation data to identify connected regions of steep terrain. A connected region of pixels is deemed *steep* if it passes two tests:
- the pixels in the region all have slope greater than a specified threshold; and
- the total elevation change within the region is greater than a second specified threshold.

Because elevation data is somewhat noisy and coarse (10 meter pixel resolution), it cannot be used to find smaller cliffs or cliff bands situated within complex terrain. Elevation data is best suited to finding tall homogenous cliff-like features.

The current script has thresholds
```javascript
var STEEP_THRESHOLD = 75;  // slope angle in degrees
var HEIGHT_THRESHOLD = 100;  // vertical height in meters
```
and searches for *big walls* terrain within the state of Utah. Results are tabulated [here](/big-wall-finder/assets/utah.csv) and can be rendered in various styles on the Earth Engine map.

The two images below are screenshots of a portion of the map around Zion National Park. Colors indicate the vertical height of individual components.


![Zion cliff bands in detail](/big-wall-finder/assets/zion1.png)

![The greater Zion region](/big-wall-finder/assets/zion2.png)