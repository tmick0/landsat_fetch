
from osgeo import gdal

from ..common import LOGGER
from ..product import product, product_set

__all__ = ['mosaic']

def mosaic_one(tup):
    band, inputs, bbox, new_file = tup
    LOGGER.info('Creating mosaic for band {}...'.format(band))
    gdal.Warp(new_file, inputs, dstSRS='+proj=longlat +ellps=WGS84', srcNodata=0, outputBounds=bbox)
    return band, new_file

def mosaic(pool, mgr, dataset, bands, bounding_box):
    mosaic_jobs = []
    for b in bands:
        mosaic_files = []
        for _, prod in dataset.products:
            mosaic_files.append(prod.band(b))
        mosaic_jobs.append((b, mosaic_files, bounding_box, mgr.add_file(suffix=".tiff")))
    return product_set({'mosaic': product(None, {band: filename for band, filename in pool.map(mosaic_one, mosaic_jobs)})})
    

