
import argparse
import pandas as pd
import multiprocessing
import urllib.request
import os
import json
import tempfile
import math
import numpy as np
from collections import defaultdict
from osgeo import gdal

gdal.AllRegister()

_base_url = "http://landsat-pds.s3.amazonaws.com/c1/L8/"

def overlaps_1d(line0, line1):
    l0x0, l0x1 = line0
    l1x0, l1x1 = line1
    return (l0x1 >= l1x0) & (l1x1 >= l0x0)

def overlaps_2d(box0, box1):
    b0y0, b0x0, b0y1, b0x1 = box0
    b1y0, b1x0, b1y1, b1x1 = box1
    return overlaps_1d((b0x0, b0x1), (b1x0, b1x1)) & overlaps_1d((b0y0, b0y1), (b1y0, b1y1))

def acquire(tup):
    prod, cat, ident, url = tup
    print('fetching {}'.format(url))
    return (prod, cat, ident, urllib.request.urlretrieve(url)[0])

def calibrate(tup):
    scene, band, orig_file, gain, bias, sun_elevation = tup
    print('calibrating scene {:s} band {:d}'.format(scene, band))

    tmpfh, new_file = tempfile.mkstemp(suffix='.tiff')
    os.close(tmpfh)
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

    outdata = None
    ds = None
    os.replace(new_file, orig_file)

def mosaic(tup):
    band, inputs, bbox = tup
    print('creating mosaic for band {:d}'.format(band))
    tmpfh, new_file = tempfile.mkstemp(suffix='.tiff')
    os.close(tmpfh)
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

    args = parser.parse_args()

    if args.band is None:
        args.band = [4, 3, 2]

    if args.scene_list is None:
        args.scene_list = _base_url + "scene_list.gz"
        print('acquiring scene list')
    else:
        print('loading scene list')

    sc = pd.read_csv(args.scene_list)
    sc_bbox = (sc.min_lat, sc.min_lon, sc.max_lat, sc.max_lon)
    req_bbox = (args.lat1, args.lon0, args.lat0, args.lon1)

    print('selecting matching scenes')
    sc = sc[overlaps_2d(sc_bbox, req_bbox) & (sc.processingLevel == 'L1TP')]
    cells_needed = [(r.path, r.row) for r in sc[['path', 'row']].drop_duplicates().itertuples()]

    files_needed = []
    for path, row in cells_needed:
        prod = next(sc[(sc.cloudCover < args.max_clouds) & (sc.path==path) & (sc.row==row)].sort_values('acquisitionDate', ascending=False).itertuples())
        prod_id = prod.productId
        scene_base_url = _base_url + '{:03d}/{:03d}/{:s}/{:s}_'.format(prod.path, prod.row, prod_id, prod_id)

        for b in args.band:
            url = scene_base_url + 'B{:d}.TIF'.format(b)
            files_needed.append((prod_id, 'band', b, url))

        if args.calibrate:
            url = scene_base_url + 'MTL.json'
            files_needed.append((prod_id, 'meta', None, url))
    
    print('need to acquire {:d} files in {:d} scenes'.format(len(files_needed), len(cells_needed)))

    pool = multiprocessing.Pool(args.num_workers)

    fetched_files = pool.map(acquire, files_needed)
    
    data = defaultdict(lambda: {})
    for scene, cat, ident, value in fetched_files:
        data[scene][(cat, ident)] = value

    if args.calibrate:
        cal_jobs = []
        for scene in data:
            with open(data[scene][('meta', None)], 'r') as fh:
                meta = json.load(fh)

            sun_elevation = math.radians(meta['L1_METADATA_FILE']['IMAGE_ATTRIBUTES']['SUN_ELEVATION'])

            for cat, band in data[scene]:
                if cat != 'band':
                    continue

                gain = (meta['L1_METADATA_FILE']['RADIOMETRIC_RESCALING']['REFLECTANCE_MULT_BAND_{:d}'.format(band)])
                bias = (meta['L1_METADATA_FILE']['RADIOMETRIC_RESCALING']['REFLECTANCE_ADD_BAND_{:d}'.format(band)])

                cal_jobs.append((scene, band, data[scene][(cat, band)], gain, bias, sun_elevation))
            
        pool.map(calibrate, cal_jobs)
                
    mosaic_jobs = []
    for b in args.band:
        mosaic_files = []
        for scene, files in data.items():
            for (cat, ident), filename in files.items():
                if cat == 'band' and ident == b:
                    mosaic_files.append(filename)
        mosaic_jobs.append((b, mosaic_files, [args.lon0, args.lat1, args.lon1, args.lat0]))
    band_mosaics = pool.map(mosaic, mosaic_jobs)

    for scene in data.values():
        for f in scene.values():
            os.unlink(f)
    
    print('merging bands')
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

    for f in band_mosaics:
        os.unlink(f)


if __name__ == '__main__':
    main()
