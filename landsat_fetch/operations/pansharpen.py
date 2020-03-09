
from osgeo import gdal
from collections import defaultdict
import xml.etree.ElementTree as ET

from ..product import product, product_set
from ..common import LOGGER 

__all__ = ['pansharpen']

def pansharpen_one(tup):
    prod_id, pan_file, spec_files, output_file = tup
    LOGGER.info("Pansharpening product {:s}...".format(prod_id))

    # adapted from https://github.com/OSGeo/gdal/blob/master/gdal/swig/python/scripts/gdal_pansharpen.py
    root = ET.Element("VRTDataset")
    root.set('subClass', 'VRTPansharpenedDataset')

    opts = ET.SubElement(root, "PansharpeningOptions")
    nodata = ET.SubElement(opts, "NoData")
    nodata.text = "0"

    pan_band_elem = ET.SubElement(opts, "PanchroBand")
    pan_band_filename = ET.SubElement(pan_band_elem, "SourceFilename")
    pan_band_filename.set("relativeToVRT", "0")
    pan_band_filename.text = pan_file
    pan_band_band = ET.SubElement(pan_band_elem, "SourceBand")
    pan_band_band.text = "1"

    for i, b in enumerate(spec_files):
        spec_band_elem = ET.SubElement(opts, "SpectralBand")
        spec_band_elem.set('dstBand', str(i + 1))
        spec_band_filename = ET.SubElement(spec_band_elem, "SourceFilename")
        spec_band_filename.set("relativeToVRT", "0")
        spec_band_filename.text = b
        spec_band_source = ET.SubElement(spec_band_elem, "SourceBand")
        spec_band_source.text = "1"

    vrt = gdal.Open(ET.tostring(root))
    gdal.GetDriverByName("GTiff").CreateCopy(output_file, vrt)

    return prod_id, output_file

def pansharpen(pool, mgr, dataset, pan_band, spectral_bands):
    pan_jobs = []
    for prod_id, prod in dataset.products:
        pan_file = prod.band(pan_band)
        spec_files = [prod.band(b) for b in spectral_bands]
        pan_jobs.append((prod_id, pan_file, spec_files, mgr.add_file(suffix=".tiff")))
    
    pan_data = defaultdict(lambda: {})
    for prod, filename in pool.map(pansharpen_one, pan_jobs):
        pan_data[prod][('band', 'pansharpened')] = filename

    return product_set({k: product(dataset[k].meta, product.get_bands(v)) for k, v in pan_data.items()})
