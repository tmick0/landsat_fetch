from collections import defaultdict
import ffmpeg as ff

from ..product import product_set, product
from ..common import LOGGER

__all__ = ['ffmpeg']

def ffmpeg_one(tup):
    band, files, rate, tmpfile, result = tup
    LOGGER.info('Creating movie for band {}...'.format(band))
    
    with open(tmpfile, 'w') as fh:
        for f in files:
            fh.write("file {}\n".format(f))
    
    ff.input(tmpfile, r=rate, f='concat', safe='0').output(result, r=30).run(overwrite_output=True, quiet=True)
    return band, result

def ffmpeg(pool, mgr, dataset, framerate):
    ffmpeg_jobs = defaultdict(lambda: [])
    for _, prod in dataset.products:
        for b, filename in prod.bands:
            ffmpeg_jobs[b].append(filename)
    ffmpeg_jobs = [(k, v, framerate, mgr.add_file(suffix='.txt'), mgr.add_file(suffix='.mp4')) for k, v in ffmpeg_jobs.items()]
    
    # bad things happened when i tried to parallelize this, so for now let's just do it this way
    ffmpeg_out = [ffmpeg_one(j) for j in ffmpeg_jobs]

    return product_set({'ffmpeg': product(None, {k: v for k, v in ffmpeg_out})})
