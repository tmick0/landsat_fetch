# landsat_fetch

A Python-based utility for automated acquisition and processing of Landsat 8 data

## Overview

`landsat_fetch` finds the latest Landsat products covering the requested geographic region (specified as a bounding box in latitude-longitude space),
optionally radiometrically corrects them (producing output in reflectance rather than DN), and mosaics them together to produce an output.

## Usage

Where `lat0` and `lon0` specify the northwest corner of the output product, and `lon1` and `lat1` represent the southwest corner, usage is simply:

```
landsat_fetch output.tiff lat0 lon0 lat1 lon1
```

Optionally, the `--calibrate` option can be added to retrieve the MTL metadata file for each fetched product and use it to convert the output to reflectance.

Currently, GeoTIFF is the only supported output format. Output is created in the equirectangular (WGS84) projection.
