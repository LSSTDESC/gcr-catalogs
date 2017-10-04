"""
Alpha Q galaxy catalog class.
"""
from __future__ import division
import os
import numpy as np
import h5py
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog
from .register import register_reader

__all__ = ['AlphaQGalaxyCatalog']

class AlphaQGalaxyCatalog(BaseGenericCatalog):
    """
    Alpha Q galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, filename, lightcone=True, **kwargs):

        assert os.path.isfile(filename), 'Catalog file {} does not exist'.format(filename)
        self._file = filename
        self.lightcone = lightcone

        self._quantity_modifiers = {
            'ra_true': (lambda x: x/3600.0, 'ra'),
            'dec_true': (lambda x: x/3600.0, 'dec'),
            'redshift_true': 'redshift',
            'shear_1': 'shear1',
            'shear_2': 'shear2',
            'convergence': 'k0',
            'magnification': 'm0',
            'halo_id': 'hostIndex',
            'halo_mass': 'hostHaloMass',
            'is_central': (lambda x : x.astype(np.bool), 'nodeIsIsolated'),
            'stellar_mass': 'totalMassStellar',
        }

        for band in 'ugriz':
            self._quantity_modifiers['mag_{}_any'.format(band)] = 'magnitude:SDSS_{}:observed'.format(band)
            self._quantity_modifiers['mag_{}_sdss'.format(band)] = 'magnitude:SDSS_{}:observed'.format(band)
            self._quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'magnitude:SDSS_{}:rest'.format(band)
            self._quantity_modifiers['Mag_true_{}_any'.format(band)] = 'magnitude:SDSS_{}:rest'.format(band)

        with h5py.File(self._file, 'r') as fh:
            self.cosmology = FlatLambdaCDM(
                H0=fh.attrs['H_0'],
                Om0=fh.attrs['Omega_matter'],
                Ob0=fh.attrs['Omega_b'],
            )


    def _generate_native_quantity_list(self):
        with h5py.File(self._file, 'r') as fh:
            native_quantities = set(fh.keys())
        return native_quantities


    def _iter_native_dataset(self, pre_filters=None):
        with h5py.File(self._file, 'r') as fh:
            yield fh


    @staticmethod
    def _fetch_native_quantity(dataset, native_quantity):
        return dataset[native_quantity].value

# Registers the reader
register_reader(AlphaQGalaxyCatalog)


#=====================================================================================================


class AlphaQClusterCatalog(AlphaQGalaxyCatalog):
    """
    The galaxy cluster catalog. Inherits AlphaQGalaxyCatalog, overloading select methods.

    The AlphaQ cluster catalog is structured in the following way: under the root hdf group, there
    is a group per each halo with SO mass above 1e14 M_sun/h. Each of these groups contains the same
    datasets as the original AlphaQ galaxy catalog, but with only as many rows as member galaxies for
    the halo in question. Each group has attributes which contain halo-wide quantities, such as mass,
    position, etc.

    This class offers filtering on any halo quantity (group attribute), as seen in all three of the
    methods of this class (all the group attributes are iterated over in contexts concerning the
    pre-filtering). The valid filtering quantities are:
    {'host_halo_mass', 'sod_halo_cdelta', 'sod_halo_cdelta_error', 'sod_halo_c_acc_mass',
     'fof_halo_tag', 'halo_index', 'halo_step', 'halo_ra', 'halo_dec', 'halo_z',
     'halo_z_err', 'sod_halo_radius', 'sod_halo_mass', 'sod_halo_ke', 'sod_halo_vel_disp'}
    """


    def _subclass_init(self, filename, **kwargs):
            super(AlphaQClusterCatalog, self)._subclass_init(filename, **kwargs)
            with h5py.File(self._file, 'r') as fh:
                self._pre_filter_quantities = set(fh[list(fh.keys())[0]].attrs)


    def _iter_native_dataset(self, pre_filters=None):
        with h5py.File(self._file, 'r') as fh:
            for key in fh:
                halo = fh[key]
                d = {}
                attrs = list(halo.attrs)
                for attr in attrs:
                    d[attr] = halo.attrs[attr]
                if (not pre_filters) or all(f[0](*(d.get(val) for val in f[1:])) for f in pre_filters):
                    yield halo


    @staticmethod
    def _fetch_native_quantity(dataset, native_quantity):
        cluster_attrs = list(dataset.attrs)
        if native_quantity in cluster_attrs:
            data = np.empty(dataset['redshift'].shape)
            data.fill(dataset.attrs['{}'.format(native_quantity)])
            return data
        return dataset[native_quantity].value


# Registers the reader
register_reader(AlphaQClusterCatalog)

