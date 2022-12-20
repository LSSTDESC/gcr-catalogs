from __future__ import division, print_function
import os
import re
from astropy.io import fits
from GCR import BaseGenericCatalog
_HAS_SKIMAGE = True
try:
    from skimage.transform import rescale
except ImportError:
    _HAS_SKIMAGE = False

__all__ = ['EImageReader']

_FILENAME_PATTERN = r'lsst_e_(\d+)(?:_f\d+)?_(R\d\d)_(S\d\d)(?:_E\d+)?(?:_[a-z])?\.fits\.gz$'

class FitsFile(object): # from buzzard.py but using hdu=0
    def __init__(self, path):
        self._path = path
        self._file_handle = None

    @staticmethod
    def _open(path):
        return fits.open(path, mode='readonly', memmap=True, lazy_load_hdus=True)

    @property
    def file_handle(self):
        if self._file_handle is None:
            try:
                self._file_handle = self._open(self._path)
            except OSError:
                if self._path.endswith('.gz') and os.path.isfile(self._path[:-3]):
                    self._file_handle = self._open(self._path[:-3])
        return self._file_handle

    @property
    def data(self):
        return self.file_handle[0].data  #pylint: disable=E1101

    def __del__(self):
        if self._file_handle is not None:
            del self._file_handle[0].data  #pylint: disable=E1101
            self._file_handle.close()
            del self._file_handle


class Sensor(object):
    def __init__(self, path, name, raft, visit, default_rebinning=None):
        self.path = path
        self.name = name
        self.raft = raft
        self.visit = visit
        self.default_rebinning = float(default_rebinning or 1)

    def get_data(self, rebinning=None):
        data = FitsFile(self.path).data
        if rebinning is None:
            rebinning = self.default_rebinning
        if rebinning != 1:
            if not _HAS_SKIMAGE:
                raise RuntimeError("scikit-image is not installed. It is requred to rescale images.")
            data = rescale(data, 1 / rebinning, mode='constant', preserve_range=True, multichannel=False, anti_aliasing=True)
        return data


class Raft(object):
    def __init__(self, name, visit):
        self.name = name
        self.visit = visit
        self.sensors = dict()

    def add_sensor(self, sensor):
        if (sensor.raft == self.name and
                sensor.visit == self.visit and
                sensor.name not in self.sensors):
            self.sensors[sensor.name] = sensor
        else:
            print('Cannot add sensor from a different raft/visit or sensor already present')


class FocalPlane(object):
    def __init__(self, visit):
        self.visit = visit
        self.rafts = dict()

    def add_raft(self, raft):
        if raft.visit == self.visit and raft.name not in self.rafts:
            self.rafts[raft.name] = raft
        else:
            print('Cannot add raft from a different visit or raft already present')

    def add_sensor(self, sensor):
        if sensor.raft not in self.rafts:
            self.add_raft(Raft(sensor.raft, sensor.visit))
        self.rafts[sensor.raft].add_sensor(sensor)


class EImageReader(BaseGenericCatalog):
    """
    E-image reader
    """

    def _subclass_init(self, root_dir, visits=None, default_rebinning=None,
                       dirpath_contain=None, filename_pattern=_FILENAME_PATTERN,
                       **kwargs):
        # pylint: disable=W0221
        if not os.path.isdir(root_dir):
            raise ValueError('`root_dir` must be a valid directory')

        if visits is not None:
            try:
                int(visits)
            except TypeError:
                visits = set(map(str, visits))
            else:
                visits = {str(visits)}
            if not visits:
                raise ValueError('`visits` is empty')
            if not all(visit.isdigit() for visit in visits):
                raise ValueError('`visits` not correctly set!')

        self.default_rebinning = float(default_rebinning or 1)
        filename_re = re.compile(filename_pattern)
        self.focal_planes = dict()
        self._valid_keys = set()

        for dirpath, _, filenames in os.walk(root_dir):
            if dirpath_contain and dirpath_contain not in dirpath:
                continue

            for filename in filenames:
                match = filename_re.match(filename)
                if not match:
                    continue

                visit, raft, sensor = match.groups()
                if visits is not None and visit not in visits:
                    continue

                if visit not in self.focal_planes:
                    self.focal_planes[visit] = FocalPlane(visit)

                sensor_this = Sensor(os.path.join(dirpath, filename), sensor, raft, visit)
                self.focal_planes[visit].add_sensor(sensor_this)

                self._valid_keys.add(visit)
                self._valid_keys.add('-'.join((visit, raft)))
                self._valid_keys.add('-'.join((visit, raft, sensor)))

        if not self.focal_planes:
            print('[WARNING] no valid image files found!!')

        # for backward compatibility
        if len(self.focal_planes) == 1:
            self.focal_plane = next(iter(self.focal_planes.values()), None)

    def __contains__(self, item):
        return item in self._valid_keys

    def __getitem__(self, key):
        if key not in self:
            raise KeyError('{} does not exist!')
        keys = key.split('-')
        focal_plane = self.focal_planes[keys.pop(0)]
        if not keys:
            return focal_plane
        raft = focal_plane.rafts[keys.pop(0)]
        if not keys:
            return raft
        return raft.sensors[keys.pop(0)]

    def _generate_native_quantity_list(self):
        return self._valid_keys

    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise ValueError('*native_filters* is not supported')
        yield self.__getitem__
