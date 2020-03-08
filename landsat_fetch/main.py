
import argparse
import multiprocessing
import shutil
from osgeo import gdal

from .filemanager import tempfilemanager
from .common import LOGGER
from .scenes import scenelist
from .product import product_set, product
from .calibrate import calibrate
from .mosaic import mosaic
from .merge import merge

gdal.AllRegister()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=str, help="Name of the output file")
    parser.add_argument("lat0", type=float, help="Northern latitude for the bounds of the mosaic (degrees)")
    parser.add_argument("lon0", type=float, help="Western longitude for the bounds of the mosaic (degrees)")
    parser.add_argument("lat1", type=float, help="Southern latitude for the bounds of the mosaic (degrees)")
    parser.add_argument("lon1", type=float, help="Eastern longitude for the bounds of the mosaic (degrees)")
    parser.add_argument("-c", "--max_clouds", type=float, default=10, help="Maximum cloud cover of fetched products (percent, default 10)")
    parser.add_argument("-b", "--band", type=int, action='append', default=None, help="Band selection for the mosaic (default is RGB)")
    parser.add_argument("-f", "--scene_list", type=str, default=None, help="Path to an existing scene list (optional)")
    parser.add_argument("-n", "--num_workers", type=int, default=4, help="Number of worker threads to use")
    parser.add_argument('--calibrate', action='store_true', default=False, help="Enable conversion from DN to reflectance")
    parser.add_argument('--keepfiles', type=str, default=None, help="Location to store source and intermediate data instead of a temporary directory")
    parser.add_argument('--pansharpen', action='store_true', default=False, help="Produce pansharpened output instead of simply merging bands")

    args = parser.parse_args()

    if args.band is None:
        args.band = [4, 3, 2]

    pool = multiprocessing.Pool(args.num_workers)

    with tempfilemanager(args.keepfiles, args.keepfiles is not None) as mgr:

        LOGGER.info("Loading scene list...")
        sc = scenelist.load_or_acquire(args.scene_list)

        LOGGER.info("Filtering scene list on processing level and footprint...")
        sc = sc.filter(lambda df: df.processingLevel == 'L1TP')
        sc = sc.filter(lambda df: scenelist.overlaps(df, args.lat1, args.lon0, args.lat0, args.lon1))

        LOGGER.info("Selecting matching paths and rows...")
        cells_needed = sc.paths_and_rows()

        LOGGER.info("Filtering scene list on cloud cover...")
        sc = sc.filter(lambda df: df.cloudCover < args.max_clouds)

        all_bands = args.band
        if args.pansharpen and not 8 in all_bands:
            all_bands = all_bands + [8]

        data = product_set.acquire(pool, mgr, sc, cells_needed, args.calibrate, all_bands)

        if args.calibrate:
            data = calibrate(pool, mgr, data)

        data = mosaic(pool, mgr, data, all_bands, [args.lon0, args.lat1, args.lon1, args.lat0])
        
        if args.pansharpen:
            # TODO
            pass
        else:
            LOGGER.info('Merging bands...')
            data = merge(mgr, data)
            shutil.move(data.band('merged'), args.output)


if __name__ == '__main__':
    main()
