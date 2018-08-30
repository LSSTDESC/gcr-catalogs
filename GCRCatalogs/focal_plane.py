from __future__ import division, print_function
import os
import glob
import pandas as pd
from astropy.io import fits
from skimage.transform import rescale
from GCR import BaseGenericCatalog

__all__ = ['FocalPlaneCatalog']


class FitsFile(object): # from buzzard.py but using hdu=0
    def __init__(self, path):
        self._path = path
        self._file_handle = fits.open(self._path, mode='readonly', memmap=True, lazy_load_hdus=True)
        self.data = self._file_handle[0].data  #pylint: disable=E1101

    def __del__(self):
        del self.data
        del self._file_handle[0].data  #pylint: disable=E1101
        self._file_handle.close()
        del self._file_handle


class Sensor(object):
    def __init__(self, path, default_rebinning=None):
        self.path = path
        self.filename = os.path.basename(path)
        aux = self.filename.split('_')
        self.parent_visit = aux[2]
        self.parent_raft = 'R{}'.format(self.filename.split('_R')[1][:2])
        self.name = 'S{}'.format(self.filename.split('_S')[1][:2])
        self.default_rebinning = float(default_rebinning or 1)

    def get_data(self, rebinning=None):
        data = FitsFile(self.path).data
        if rebinning is None:
            rebinning = self.default_rebinning
        if rebinning != 1:
            data = rescale(data, 1 / rebinning, mode='constant', preserve_range=True, multichannel=False, anti_aliasing=True)
        return data

class Raft(object):
    def __init__(self, name, visit):
        self.name = name
        self.visit = visit
        self.sensors = dict()

    def add_sensor(self, sensor):
        if sensor.parent_raft == self.name and \
                sensor.parent_visit == self.visit and \
                sensor.name not in self.sensors:
            self.sensors[sensor.name] = sensor
        else:
            print('Cannot add sensor from a different raft/visit or sensor already present')


class FocalPlane(object):
    def __init__(self, visit):
        visit = str(visit)
        self.visit = visit
        self.rafts = dict()

    def add_raft(self, raft):
        if raft.visit == self.visit and raft.name not in self.rafts:
            self.rafts[raft.name] = raft
        else:
            print('Cannot add raft from a different visit or raft already present')

    def add_sensor(self, sensor):
        if sensor.parent_raft not in self.rafts:
            self.add_raft(Raft(sensor.parent_raft, sensor.parent_visit))
        self.rafts[sensor.parent_raft].add_sensor(sensor)


class FocalPlaneCatalog(BaseGenericCatalog):
    """
    Catalog containing information about images in a single focal plane/visit
    """

    def _subclass_init(self, catalog_root_dir, rebinning=None, **kwargs):
        #pylint: disable=W0221
        if (not os.path.isdir(catalog_root_dir)) and ('*' not in catalog_root_dir):
            raise ValueError('Catalog directory {} does not exist'.format(catalog_root_dir))
        self._filelist = glob.glob(os.path.join(catalog_root_dir, 'lsst_e*.fits*'))
        self.rebinning = float(rebinning or 1)
        parent_path = os.path.dirname(catalog_root_dir)
        try:
            instcat_path = glob.glob(os.path.join(parent_path, 'instCat/phosim*.txt'))[0]
        except IndexError:
            print('No instance catalog found in the expected path')
            self.phosim_pars = None
            self.visit = os.path.split(self._filelist[0])[1].split('_')[2]
        else:
            self.phosim_pars = pd.read_table(instcat_path, index_col=0, header=None, sep=' ').T
            self.visit = self.phosim_pars['obshistid'].values[0]

        self.focal_plane = FocalPlane(self.visit)

    def _load_focal_plane(self):
        for fname in self._filelist:
            self.focal_plane.add_sensor(Sensor(fname, default_rebinning=self.rebinning))

    def _generate_native_quantity_list(self):
        native_quantity_list = {'visit'}
        self._load_focal_plane()
        for raft_name, raft in self.focal_plane.rafts.items():
            native_quantity_list.add(raft_name)
            for sensor_name in raft.sensors:
                native_quantity_list.add('-'.join((raft_name, sensor_name)))
        return native_quantity_list

    def _native_quantity_getter(self, native_quantity):
        if native_quantity == 'visit':
            self._load_focal_plane()
            return self.focal_plane
        if '-' in native_quantity:
            raft_name, sensor_name = native_quantity.split('-')
            sensor = self.focal_plane.rafts[raft_name].sensors[sensor_name]
            return sensor
        if '-' not in native_quantity:
            return self.focal_plane.rafts[native_quantity]

    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise ValueError('*native_filters* is not supported')
        yield self._native_quantity_getter
