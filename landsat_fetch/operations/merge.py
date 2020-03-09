from osgeo import gdal

from ..product import product, product_set
from ..common import LOGGER

__all__ = ["merge"]

def merge_one(tup):
    prod_id, files, filename = tup

    LOGGER.info('Merging bands for product {:s}...'.format(prod_id))

    driver = gdal.GetDriverByName("GTiff")
    datasets = [gdal.Open(f) for f in files]
    
    outdata = None
    for i, ds in enumerate(datasets):
        arr = ds.GetRasterBand(1).ReadAsArray()
        if outdata is None:
            rows, cols = arr.shape
            outdata = driver.Create(filename, cols, rows, len(datasets), gdal.GDT_Float32)
            outdata.SetGeoTransform(ds.GetGeoTransform())
            outdata.SetProjection(ds.GetProjection())
        outdata.GetRasterBand(i + 1).WriteArray(arr)
    outdata.FlushCache()
    
    return prod_id, filename

def merge(pool, mgr, dataset):
    merge_jobs = []
    for prod_id, prod in dataset.products:
        filenames = [f for _, f in prod.bands]
        merge_jobs.append((prod_id, filenames, mgr.add_file(suffix=".tiff")))
    return product_set({k: product(dataset[k].meta, {'merged': v}) for k, v in pool.map(merge_one, merge_jobs)})
