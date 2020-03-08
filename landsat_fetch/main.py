
import argparse
import pandas as pd
import multiprocessing
import os
import math
import numpy as np
from osgeo import gdal
from collections import defaultdict

from .filemanager import tempfilemanager
from .common import LANDSAT_8_URL, LOGGER
from .scenes import scenelist
from .product import product_set, product

gdal.AllRegister()

def calibrate(tup):
    prod, band, orig_file, gain, bias, sun_elevation, new_file = tup
    LOGGER.info('Calibrating product {:s} band {:d}...'.format(prod, band))

    ds = gdal.Open(orig_file)
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    rows, cols = arr.shape

    # calibration formula from https://www.usgs.gov/land-resources/nli/landsat/using-usgs-landsat-level-1-data-product
    arr[arr != 0] = (arr[arr != 0] * gain + bias) / np.sin(sun_elevation)

    driver = gdal.GetDriverByName("GTiff")
    outdata = driver.Create(new_file, cols, rows, 1, gdal.GDT_Float32)
    outdata.SetGeoTransform(ds.GetGeoTransform())
    outdata.SetProjection(ds.GetProjection())
    outdata.GetRasterBand(1).WriteArray(arr)
    outdata.FlushCache()

    return prod, band, new_file

def mosaic(tup):
    band, inputs, bbox, new_file = tup
    LOGGER.info('Creating mosaic for band {:d}...'.format(band))
    gdal.Warp(new_file, inputs, dstSRS='+proj=longlat +ellps=WGS84', srcNodata=0, outputBounds=bbox)
    return new_file

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=str)
    parser.add_argument("lat0", type=float)
    parser.add_argument("lon0", type=float)
    parser.add_argument("lat1", type=float)
    parser.add_argument("lon1", type=float)
    parser.add_argument("-c", "--max_clouds", type=float, default=10)
    parser.add_argument("-b", "--band", type=int, action='append', default=None)
    parser.add_argument("-f", "--scene_list", type=str, default=None)
    parser.add_argument("-n", "--num_workers", type=int, default=4)
    parser.add_argument('--calibrate', action='store_true', default=False)
    parser.add_argument('--keepfiles', type=str, default=None)

    args = parser.parse_args()

    if args.band is None:
        args.band = [4, 3, 2]

    pool = multiprocessing.Pool(args.num_workers)

    with tempfilemanager(args.keepfiles, args.keepfiles is not None) as mgr:

        LOGGER.info("Loading scene list...")
        sc = scenelist.load_or_acquire(args.scene_list)

        LOGGER.info("Filtering scene list on processing level and footprint...")
        sc = sc.filter(lambda df: df.processingLevel == 'L1TP')
        sc = sc.filter(lambda df: scenelist.overlaps(df, args.lat1, args.lon0, args.lat0, args.lon1))

        LOGGER.info("Selecting matching paths and rows...")
        cells_needed = sc.paths_and_rows()

        LOGGER.info("Filtering scene list on cloud cover...")
        sc = sc.filter(lambda df: df.cloudCover < args.max_clouds)

        data = product_set.acquire(pool, mgr, sc, cells_needed, args.calibrate, args.band)

        if args.calibrate:
            cal_jobs = []
            for prod_id, prod in data.products:
                sun_elevation = math.radians(prod.meta['L1_METADATA_FILE']['IMAGE_ATTRIBUTES']['SUN_ELEVATION'])
                for band, filename in prod.bands:
                    gain = prod.meta['L1_METADATA_FILE']['RADIOMETRIC_RESCALING']['REFLECTANCE_MULT_BAND_{:d}'.format(band)]
                    bias = prod.meta['L1_METADATA_FILE']['RADIOMETRIC_RESCALING']['REFLECTANCE_ADD_BAND_{:d}'.format(band)]
                    cal_jobs.append((prod_id, band, filename, gain, bias, sun_elevation, mgr.add_file(suffix=".tiff")))
            
            calibrated_data = defaultdict(lambda: {})
            for prod, band, filename in pool.map(calibrate, cal_jobs):
                calibrated_data[prod][('band', band)] = filename

            data = product_set({k: product(data[k].meta, product.get_bands(v)) for k, v in calibrated_data.items()})

        mosaic_jobs = []
        for b in args.band:
            mosaic_files = []
            for _, prod in data.products:
                mosaic_files.append(prod.band(b))
            mosaic_jobs.append((b, mosaic_files, [args.lon0, args.lat1, args.lon1, args.lat0], mgr.add_file(suffix=".tiff")))
        band_mosaics = pool.map(mosaic, mosaic_jobs)
        
        LOGGER.info('Merging bands...')
        driver = gdal.GetDriverByName("GTiff")
        datasets = [gdal.Open(f) for f in band_mosaics]
        
        outdata = None
        for i, ds in enumerate(datasets):
            arr = ds.GetRasterBand(1).ReadAsArray()
            if outdata is None:
                rows, cols = arr.shape
                outdata = driver.Create(args.output, cols, rows, len(datasets), gdal.GDT_Float32)
                outdata.SetGeoTransform(ds.GetGeoTransform())
                outdata.SetProjection(ds.GetProjection())
            outdata.GetRasterBand(i + 1).WriteArray(arr)
        outdata.FlushCache()
        outdata = None


if __name__ == '__main__':
    main()
