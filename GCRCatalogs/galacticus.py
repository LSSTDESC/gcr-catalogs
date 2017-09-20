"""
Galacticus galaxy catalog class.
"""
from __future__ import division
import os
import numpy as np
import h5py
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog
from .register import register_reader

__all__ = ['GalacticusGalaxyCatalog']


class GalacticusGalaxyCatalog(BaseGenericCatalog):
    """
    Argonne galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, filename, base_catalog_dir=os.curdir, **kwargs):

        self._pre_filter_quantities = {'cosmological_redshift'}

        self._quantity_modifiers = {
            'stellar_mass': (lambda x: x**10.0, 'log_stellarmass'),
        }

        self._file = os.path.join(base_catalog_dir, filename)

        with h5py.File(self._file, 'r') as fh:
            self.cosmology = FlatLambdaCDM(
                H0=fh['cosmology'].attrs['H_0'],
                Om0=fh['cosmology'].attrs['Omega_Matter'],
            )


    def _generate_native_quantity_list(self):
        with h5py.File(self._file, 'r') as fh:
            for k in fh:
                if k != 'cosmology':
                    native_quantities = fh[k].keys()
                    break
        native_quantities.append('cosmological_redshift')
        return native_quantities


    def _iter_native_dataset(self, pre_filters=None):
        with h5py.File(self._file, 'r') as fh:
            for key in fh:
                if key == 'cosmology':
                    continue
                d = fh[key]
                z = d.attrs['z']
                if (not pre_filters) or all(f[0](*([z]*(len(f)-1))) for f in pre_filters):
                    yield d


    @staticmethod
    def _fetch_native_quantity(dataset, native_quantity):
        if native_quantity == 'cosmological_redshift':
            data = np.empty(dataset['redshift'].shape)
            data.fill(dataset.attrs['z'])
            return data
        return dataset[native_quantity].value

# Registers the reader
register_reader(GalacticusGalaxyCatalog)
