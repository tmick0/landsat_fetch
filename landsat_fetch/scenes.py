import pandas as pd

from .common import LANDSAT_8_URL, LOGGER
from .product import product_index_entry

__all__ = ['scenelist']

def overlaps_1d(line0, line1):
    l0x0, l0x1 = line0
    l1x0, l1x1 = line1
    return (l0x1 >= l1x0) & (l1x1 >= l0x0)

def overlaps_2d(box0, box1):
    b0y0, b0x0, b0y1, b0x1 = box0
    b1y0, b1x0, b1y1, b1x1 = box1
    return overlaps_1d((b0x0, b0x1), (b1x0, b1x1)) & overlaps_1d((b0y0, b0y1), (b1y0, b1y1))

class scenelist (object):
    def __init__(self, pd_obj):
        self._df = pd_obj
    
    def filter(self, func):
        return self.__class__(self._df[func(self._df)])
    
    def sort(self, *args, **kwargs):
        return self.__class__(self._df.sort_values(*args, **kwargs))
    
    def first(self):
        return product_index_entry(next(self._df.itertuples()))
    
    def paths_and_rows(self):
        return [(r.path, r.row) for r in self._df[['path', 'row']].drop_duplicates().itertuples()]

    @staticmethod
    def overlaps(df, *bbox):
        return overlaps_2d((df.min_lat, df.min_lon, df.max_lat, df.max_lon), bbox)

    @classmethod
    def load_or_acquire(cls, path=None):
        if path is None:
            path = LANDSAT_8_URL + "scene_list.gz"
        return cls(pd.read_csv(path))
