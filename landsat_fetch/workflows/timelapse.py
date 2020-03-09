
import multiprocessing
import shutil
import numpy as np

from ..filemanager import tempfilemanager
from ..common import LOGGER
from ..scenes import scenelist
from ..product import product_set, product
from ..operations.calibrate import calibrate
from ..operations.reproject import reproject
from ..operations.merge import merge
from ..operations.to_jpeg import to_jpeg
from ..operations.ffmpeg import ffmpeg

__all__ = ['timelapse_workflow']

class timelapse_workflow (object):
    @classmethod
    def register(cls, subparsers):
        parser = subparsers.add_parser('timelapse')
        parser.add_argument("output", type=str, help="Name of the output file")
        parser.add_argument("path", type=int, help="WRS path to fetch")
        parser.add_argument("row", type=int, help="WRS row to fetch")
        parser.add_argument("start", type=str, help="ISO datetime string for start of timelapse")
        parser.add_argument("end", type=str, help="ISO datetime string for end of timelapse")
        parser.add_argument("-w", "--width", type=int, help="Width of output in pixels", default=1080)
        parser.add_argument("-r", "--rate", type=int, help="Frame rate", default=15)
        parser.add_argument("-b", "--band", type=int, action='append', default=None, help="Band selection for the composite (default is RGB)")
        parser.add_argument("-f", "--scene_list", type=str, default=None, help="Path to an existing scene list (optional)")
        parser.add_argument("-n", "--num_workers", type=int, default=4, help="Number of worker threads to use")
        parser.add_argument('--calibrate', action='store_true', default=False, help="Enable conversion from DN to reflectance")
        parser.add_argument('--keepfiles', type=str, default=None, help="Location to store source and intermediate data instead of a temporary directory")
        parser.set_defaults(func=cls.run)
    
    @classmethod
    def run(cls, args):
        if args.band is None:
            args.band = [4, 3, 2]

        if args.calibrate:
            scale_parms = [0, 1, 0, 255]
        else:
            scale_parms = [0, 65536, 0, 255]

        pool = multiprocessing.Pool(args.num_workers)

        with tempfilemanager(args.keepfiles, args.keepfiles is not None) as mgr:

            LOGGER.info("Loading scene list...")
            sc = scenelist.load_or_acquire(args.scene_list)

            LOGGER.info("Filtering scene list...")
            sc = sc.filter(lambda df: (df.row == args.row) & (df.path == args.path) & (df.acquisitionDate >= args.start) & (df.acquisitionDate <= args.end))
            sc = sc.sort('acquisitionDate')
            sc = sc.remove_duplicates()

            min_lat = np.inf
            max_lat = -np.inf
            min_lon = np.inf
            max_lon = -np.inf

            for row in sc.df().itertuples():
                min_lat = min(min_lat, row.min_lat)
                max_lat = max(max_lat, row.max_lat)
                min_lon = min(min_lon, row.min_lon)
                max_lon = max(max_lon, row.max_lon)

            data = product_set.acquire(pool, mgr, sc, [(args.path, args.row)], args.calibrate, args.band, most_recent_only=False)

            if args.calibrate:
                data = calibrate(pool, mgr, data)

            data = reproject(pool, mgr, data, [min_lon, min_lat, max_lon, max_lat])
            data = merge(pool, mgr, data)
            data = to_jpeg(pool, mgr, data, scale_parms, args.width)
            data = ffmpeg(pool, mgr, data, args.rate)
            shutil.move(data['ffmpeg'].band('merged'), args.output)           
