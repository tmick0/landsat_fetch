
import tempfile
import os
import os.path

__all__ = ['tempfilemanager']

class tempfilemanager (object):
    def __init__(self, prefix=None, persist=False):
        if prefix is None:
            prefix = tempfile.mkdtemp()
            self._rmdir = True
        else:
            os.makedirs(prefix, mode=0o700, exist_ok=True)
            self._rmdir = False
        self._prefix = prefix
        self._files = []
        self._persist = persist

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self._persist:
            for f in self._files:
                try:
                    os.unlink(f)
                except:
                    pass
            if self._rmdir:
                os.rmdir(self._prefix)

    def add_file(self, name=None, suffix=None):
        if name == None:
            fd, name = tempfile.mkstemp(dir=self._prefix, suffix=suffix)
            os.close(fd)
        self._files.append(name)
        return name
