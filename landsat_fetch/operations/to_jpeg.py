from collections import defaultdict
from osgeo import gdal

from ..product import product_set, product
from ..common import LOGGER

__all__ = ['to_jpeg']

def to_jpeg_one(tup):
    prod, band, orig_file, scale_parms, width, new_file = tup
    LOGGER.info('Converting product {:s} band {}...'.format(prod, band))

    ds = gdal.Open(orig_file)
    gdal.Translate(new_file, ds, width=width, scaleParams=[scale_parms], outputType=gdal.GDT_Byte)

    return prod, band, new_file

def to_jpeg(pool, mgr, dataset, scale_parms, width):
    jpeg_jobs = []
    for prod_id, prod in dataset.products:
        for band, filename in prod.bands:
            jpeg_jobs.append((prod_id, band, filename, scale_parms, width, mgr.add_file(suffix=".jpeg")))
    
    transformed_data = defaultdict(lambda: {})
    for prod, band, filename in pool.map(to_jpeg_one, jpeg_jobs):
        transformed_data[prod][('band', band)] = filename

    return product_set({k: product(dataset[k].meta, product.get_bands(v)) for k, v in transformed_data.items()})
