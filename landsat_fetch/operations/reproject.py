from collections import defaultdict
from osgeo import gdal

from ..product import product_set, product
from ..common import LOGGER

__all__ = ['reproject']

def reproject_one(tup):
    prod, band, orig_file, bbox, new_file = tup
    LOGGER.info('Reprojecting product {} band {}...'.format(prod, band))
    gdal.Warp(new_file, [orig_file], dstSRS='+proj=longlat +ellps=WGS84', srcNodata=0, outputBounds=bbox)

    return prod, band, new_file

def reproject(pool, mgr, dataset, bounding_box):
    proj_jobs = []
    for prod_id, prod in dataset.products:
        for band, filename in prod.bands:
            proj_jobs.append((prod_id, band, filename, bounding_box, mgr.add_file(suffix=".tiff")))
    
    reproj_data = defaultdict(lambda: {})
    for prod, band, filename in pool.map(reproject_one, proj_jobs):
        reproj_data[prod][('band', band)] = filename

    return product_set({k: product(dataset[k].meta, product.get_bands(v)) for k, v in reproj_data.items()})
