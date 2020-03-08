from osgeo import gdal

from .product import product

def merge(mgr, prod):
    driver = gdal.GetDriverByName("GTiff")
    datasets = [gdal.Open(f) for _, f in prod.bands]
    filename = mgr.add_file(suffix='.tiff')
    
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
    
    return product(None, {'merged': filename})
