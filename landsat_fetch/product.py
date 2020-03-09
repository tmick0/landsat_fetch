
import urllib.request
from collections import defaultdict
import json
import os

from .common import LANDSAT_8_URL, LOGGER

__all__ = ["product_index_entry", "product", "product_set"]

class product_index_entry (object):
    def __init__(self, tup):
        self._id = tup.productId
        self._base_url = LANDSAT_8_URL + '{:03d}/{:03d}/{:s}/{:s}_'.format(tup.path, tup.row, tup.productId, tup.productId)

    @property
    def id(self):
        return self._id
    
    def metadata_url(self):
        return self._base_url + "MTL.json"
    
    def band_url(self, band):
        return self._base_url + "B{:d}.TIF".format(band)

class product (object):
    def __init__(self, meta, bands):
        self._meta = meta
        self._bands = bands

    @property
    def meta(self):
        return self._meta

    @classmethod
    def get_metadata(cls, d):
        try:
            filename = d[('meta', None)]
        except KeyError:
            return None

        with open(filename, 'r') as fh:
            res = json.load(fh)
        os.unlink(filename)

        return res
    
    @property
    def bands(self):
        return self._bands.items()

    @classmethod
    def get_bands(cls, d):
        return {k: v for (cat, k), v in d.items() if cat == 'band'}

    def band(self, b):
        return self._bands[b]

class product_set (object):

    def __init__(self, data):
        self._dict = data

    @property
    def products(self):
        return self._dict.items()

    def __getitem__(self, key):
        return self._dict[key]

    @classmethod
    def _acquire_one(cls, tup):
        prod, cat, ident, url, filename = tup
        LOGGER.info('Fetching {:s}...'.format(url))
        return (prod, cat, ident, urllib.request.urlretrieve(url, filename)[0])

    @classmethod
    def acquire(cls, pool, mgr, scene_df, scenes, include_metadata, bands, most_recent_only=True):
        files_needed = []
        for path, row in scenes:
            if most_recent_only:
                prod = [scene_df.filter(lambda df: (df.path == path) & (df.row == row)).sort('acquisitionDate', ascending=True).first()]
            else:
                prod = scene_df.filter(lambda df: (df.path == path) & (df.row == row)).all()
            for b in bands:
                for p in prod:
                    files_needed.append((p.id, 'band', b, p.band_url(b), mgr.add_file(suffix='.tiff')))
            if include_metadata:
                for p in prod:
                    files_needed.append((p.id, 'meta', None, p.metadata_url(), mgr.add_file(suffix='.json')))
        
        LOGGER.info('Acquiring {:d} files in {:d} scenes...'.format(len(files_needed), len(scenes)))
        fetched_files = pool.map(cls._acquire_one, files_needed)
        
        data = defaultdict(lambda: {})
        for scene, cat, ident, value in fetched_files:
            data[scene][(cat, ident)] = value
        
        return cls({k: product(product.get_metadata(v), product.get_bands(v)) for k, v in data.items()})
