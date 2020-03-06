
import argparse
import pandas as pd
import multiprocessing
import urllib.request
import os
from osgeo import gdal

_base_url = "http://landsat-pds.s3.amazonaws.com/c1/L8/"

def overlaps_1d(line0, line1):
    l0x0, l0x1 = line0
    l1x0, l1x1 = line1
    return (l0x1 >= l1x0) & (l1x1 >= l0x0)

def overlaps_2d(box0, box1):
    b0y0, b0x0, b0y1, b0x1 = box0
    b1y0, b1x0, b1y1, b1x1 = box1
    return overlaps_1d((b0x0, b0x1), (b1x0, b1x1)) & overlaps_1d((b0y0, b0y1), (b1y0, b1y1))

def acquire(url):
    print('fetching {}'.format(url))
    return urllib.request.urlretrieve(url)[0] #, url.split('/')[-1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=str)
    parser.add_argument("lat0", type=float)
    parser.add_argument("lon0", type=float)
    parser.add_argument("lat1", type=float)
    parser.add_argument("lon1", type=float)
    parser.add_argument("-c", "--max_clouds", type=float, default=10)
    parser.add_argument("-b", "--band", type=int, default=4)
    parser.add_argument("-f", "--scene_list", type=str, default=None)
    parser.add_argument("-n", "--num_workers", type=int, default=4)

    args = parser.parse_args()

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

    print('need to acquire {:d} scenes'.format(len(cells_needed)))

    files_needed = []
    for path, row in cells_needed:
        prod = next(sc[(sc.cloudCover < args.max_clouds) & (sc.path==path) & (sc.row==row)].sort_values('acquisitionDate', ascending=False).itertuples())
        url = _base_url + '{:03d}/{:03d}/{:s}/{:s}_B{:d}.TIF'.format(prod.path, prod.row, prod.productId, prod.productId, args.band)
        files_needed.append(url)

    pool = multiprocessing.Pool(args.num_workers)

    files = pool.map(acquire, files_needed)

    print('creating mosaic')
    gdal.Warp(args.output, files, dstSRS='+proj=longlat +ellps=WGS84', srcNodata=0, outputBounds=[args.lon0, args.lat1, args.lon1, args.lat0])

    for f in files:
       os.unlink(f)


if __name__ == '__main__':
    main()
