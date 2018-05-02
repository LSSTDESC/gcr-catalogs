"""
redMaPPer catalog class.
"""
from __future__ import division, print_function
import os
import functools
import numpy as np
from astropy.io import fits
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog

__all__ = ['RedMapperCatalog']


class FitsFile(object):
    def __init__(self, path):
        self._path = path
        self._file_handle = fits.open(self._path, mode='readonly', memmap=True, lazy_load_hdus=True)
        self.data = self._file_handle[1].data #pylint: disable=E1101

    def __del__(self):
        del self.data
        del self._file_handle[1].data #pylint: disable=E1101
        self._file_handle.close()
        del self._file_handle


class RedMapperCatalog(BaseGenericCatalog):
    """
    Buzzard galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, catalog_root_dir,
                       catalog_path_template,
                       use_cache=True,
                       **kwargs): #pylint: disable=W0221

        assert(os.path.isdir(catalog_root_dir)), 'Catalog directory {} does not exist'.format(catalog_root_dir)

        self._catalog_path_template = {k: os.path.join(catalog_root_dir, v) for k, v in catalog_path_template.items()}
        self.cosmology = FlatLambdaCDM(**kwargs.get('cosmology'))
        self.lightcone = kwargs.get('lightcone')
        self.sky_area = kwargs.get('sky_area')

        _c = 299792.458
        _mask_func = lambda x: np.where(x==99.0, np.nan, x)

        self.cache = dict() if use_cache else None

        # specify quantity modifiers
        self._quantity_modifiers = {
            'galaxy_id'         :   'members/ID',
            'cluster_id_member' :   'members/MEM_MATCH_ID',
            'ra'                :   'members/RA',
            'dec'               :   'members/DEC',
            'cluster_id'        :   'clusters/MEM_MATCH_ID',
            'ra_cluster'        :   'clusters/RA',
            'dec_cluster'       :   'clusters/DEC',
            'redshift_true'     :   'members/Z',
            'redshift'          :   'members/ZRED',
            'redshift_cluster'  :   'clusters/Z_LAMBDA',
            'redshift_true_cluster'  :   'clusters/Z',
            'p_mem'             :   'members/P',
            'p_free'            :   'members/PFREE',
            'p_cen'             :   'clusters/P_BCG',
            'richness'          :   'clusters/LAMBDA_CHISQ',
            'halo_id'           :   'clusters/MEM_MATCH_ID',
            'halo_mass'         :   'clusters/M200',
            'lim_limmag_dered'  :   'clusters/LIM_LIMMAG_DERED',
            'scaleval'          :   'clusters/SCALEVAL',
        }

        # add magnitudes
        for i, band in enumerate(['u','g','r','i','z']):
            self._quantity_modifiers['mag_{}_lsst'.format(band)] = 'members/MODEL_MAG/{}'.format(i)
            self._quantity_modifiers['magerr_{}_lsst'.format(band)] = 'members/MODEL_MAGERR/{}'.format(i)

    def _iter_native_dataset(self, native_filters=None):
        assert not native_filters, '*native_filters* is not supported'

        yield functools.partial(self._native_quantity_getter)

    def _generate_native_quantity_list(self):
        native_quantities = set()

        for subset in self._catalog_path_template.keys():
            f = self._open_dataset(subset)
            for name, (dt, _) in f.data.dtype.fields.items():
                if dt.shape:
                    for i in range(dt.shape[0]):
                        native_quantities.add('/'.join((subset, name, str(i))))
                else:
                    native_quantities.add('/'.join((subset, name)))
        return native_quantities

    def _open_dataset(self, subset):
        path = self._catalog_path_template[subset]

        if self.cache is None:
            return FitsFile(path)

        key = (subset)
        if key not in self.cache:
            self.cache[key] = FitsFile(path)
        return self.cache[key]


    def _native_quantity_getter(self, native_quantity):

        native_quantity = native_quantity.split('/')
        assert len(native_quantity) in {2,3}, 'something wrong with the native_quantity {}'.format(native_quantity)
        subset = native_quantity.pop(0)
        column = native_quantity.pop(0)
        data = self._open_dataset(subset).data[column]
        if native_quantity:
            data = data[:,int(native_quantity.pop(0))]
        return data.byteswap().newbyteorder()
