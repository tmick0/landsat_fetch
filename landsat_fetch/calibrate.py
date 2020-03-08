
import numpy as np
from collections import defaultdict
from osgeo import gdal

from .product import product_set, product
from .common import LOGGER

__all__ = ['calibrate']

def calibrate_one(tup):
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

def calibrate(pool, mgr, dataset):
    cal_jobs = []
    for prod_id, prod in dataset.products:
        sun_elevation = np.deg2rad(prod.meta['L1_METADATA_FILE']['IMAGE_ATTRIBUTES']['SUN_ELEVATION'])
        for band, filename in prod.bands:
            gain = prod.meta['L1_METADATA_FILE']['RADIOMETRIC_RESCALING']['REFLECTANCE_MULT_BAND_{:d}'.format(band)]
            bias = prod.meta['L1_METADATA_FILE']['RADIOMETRIC_RESCALING']['REFLECTANCE_ADD_BAND_{:d}'.format(band)]
            cal_jobs.append((prod_id, band, filename, gain, bias, sun_elevation, mgr.add_file(suffix=".tiff")))
    
    calibrated_data = defaultdict(lambda: {})
    for prod, band, filename in pool.map(calibrate_one, cal_jobs):
        calibrated_data[prod][('band', band)] = filename

    return product_set({k: product(dataset[k].meta, product.get_bands(v)) for k, v in calibrated_data.items()})