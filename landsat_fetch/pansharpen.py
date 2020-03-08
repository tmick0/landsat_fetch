
from osgeo import gdal
import xml.etree.ElementTree as ET

from .product import product

__all__ = ['pansharpen']

# adapted from https://github.com/OSGeo/gdal/blob/master/gdal/swig/python/scripts/gdal_pansharpen.py
def pansharpen(mgr, dataset, pan_band, spectral_bands):

    result = mgr.add_file(suffix='.tiff')

    root = ET.Element("VRTDataset")
    root.set('subClass', 'VRTPansharpenedDataset')

    opts = ET.SubElement(root, "PansharpeningOptions")
    nodata = ET.SubElement(opts, "NoData")
    nodata.text = "0"

    pan_band_elem = ET.SubElement(opts, "PanchroBand")
    pan_band_filename = ET.SubElement(pan_band_elem, "SourceFilename")
    pan_band_filename.set("relativeToVRT", "0")
    pan_band_filename.text = dataset.band(pan_band)
    pan_band_band = ET.SubElement(pan_band_elem, "SourceBand")
    pan_band_band.text = "1"

    for i, b in enumerate(spectral_bands):
        spec_band_elem = ET.SubElement(opts, "SpectralBand")
        spec_band_elem.set('dstBand', str(i + 1))
        spec_band_filename = ET.SubElement(spec_band_elem, "SourceFilename")
        spec_band_filename.set("relativeToVRT", "0")
        spec_band_filename.text = dataset.band(b)
        spec_band_source = ET.SubElement(spec_band_elem, "SourceBand")
        spec_band_source.text = "1"

    vrt = gdal.Open(ET.tostring(root))
    gdal.GetDriverByName("GTiff").CreateCopy(result, vrt)
    return product(None, {'pansharpened': result})
