"""
Buzzard galaxy catalog class.
"""
from __future__ import division, print_function
import os
import numpy as np
from astropy.io import fits
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog
from .register import register_reader

__all__ = ['BuzzardGalaxyCatalog']


def _get_fits_data(fits_file):
    return fits_file[1].data


class BuzzardGalaxyCatalog(BaseGenericCatalog):
    """
    Argonne galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self,
                       base_catalog_dir=os.curdir,
                       catalog_main_dir=os.curdir,
                       catalog_sub_dirs={'truth':'truth'},
                       cosmo_h=0.7,
                       cosmo_Omega_M0=0.286,
                       npix=768,
                       filename_template='Chinchilla-0_lensed.{}.fits',
                       halo_mass_def='vir',
                       **kwargs):

        self._pre_filter_quantities = {'original_healpixel'}
        self.cosmology = FlatLambdaCDM(H0=cosmo_h*100.0, Om0=cosmo_Omega_M0)
        self._halo_mass_def = halo_mass_def

        _c = 299792.458
        self._quantity_modifiers = {
            'galaxy_id': ('truth', 'ID'),
            'redshift': (lambda zt, x, y, z, vx, vy, vz: zt + (x*vx+y*vy+z*vz)/np.sqrt(x*x+y*y+z*z)/_c,
                ('truth', 'Z'), ('truth', 'PX'), ('truth', 'PY'), ('truth', 'PZ'), ('truth', 'VX'), ('truth', 'VY'), ('truth', 'VZ')),
            'redshift_true': ('truth', 'Z'),
            'ra': ('truth', 'RA'),
            'dec': ('truth', 'DEC'),
            'ra_true': ('truth', 'TRA'),
            'dec_true': ('truth', 'TDEC'),
            'halo_id': ('truth', 'HALOID'),
            'halo_mass': (lambda x: x/self.cosmology.h, ('truth', 'M200')),
            'is_central': (lambda x: x.astype(np.bool), ('truth', 'CENTRAL')),
            'ellipticity_1': ('truth', 'EPSILON', 0),
            'ellipticity_2': ('truth', 'EPSILON', 1),
            'ellipticity_1_true': ('truth', 'TE', 0),
            'ellipticity_2_true': ('truth', 'TE', 1),
            'size': ('truth', 'SIZE'),
            'size_true': ('truth', 'TSIZE'),
            'shear_1': ('truth', 'GAMMA1'),
            'shear_2': ('truth', 'GAMMA2'),
            'convergence': ('truth', 'KAPPA'),
            'magnification': ('truth', 'MU'),
            'position_x': (lambda x: x/self.cosmology.h, ('truth', 'PX')),
            'position_y': (lambda x: x/self.cosmology.h, ('truth', 'PY')),
            'position_z': (lambda x: x/self.cosmology.h, ('truth', 'PZ')),
            'velocity_x': ('truth', 'VX'),
            'velocity_y': ('truth', 'VY'),
            'velocity_z': ('truth', 'VZ'),
        }

        _abs_mask_func = lambda x: np.where(x==99.0, np.nan, x + 5 * np.log10(self.cosmology.h))
        _mask_func = lambda x: np.where(x==99.0, np.nan, x)
        for i, b in enumerate('grizY'):
            self._quantity_modifiers['Mag_true_{}_des_z01'.format(b)] = (_abs_mask_func, ('truth', 'AMAG', i))
            self._quantity_modifiers['Mag_true_{}_any'.format(b)] = (_abs_mask_func, ('truth', 'AMAG', i))
            self._quantity_modifiers['mag_{}_des'.format(b)] = (_mask_func, ('truth', 'OMAG', i))
            self._quantity_modifiers['mag_{}_any'.format(b)] = (_mask_func, ('truth', 'OMAG', i))
            self._quantity_modifiers['magerr_{}_des'.format(b)] = (_mask_func, ('truth', 'OMAGERR', i))
            self._quantity_modifiers['magerr_{}_any'.format(b)] = (_mask_func, ('truth', 'OMAGERR', i))

        self._catalog_sub_dirs = {k: os.path.join(base_catalog_dir, catalog_main_dir, v) for k, v in catalog_sub_dirs.items()}
        self._npix = npix
        self._filename_template = filename_template
        self._healpixel_list = list(range(self._npix))


    def set_healpixel_list(self, healpixel_list=None):
        """
        Set the list of healpixels used by the reader.

        Parameters
        ----------
        healpixel_list : list, optional
            if None, reset the healpixel list
        """
        if not healpixel_list:
            self._healpixel_list = list(range(self._npix))
        else:
            self._healpixel_list = list(healpixel_list)


    def _generate_native_quantity_list(self):
        native_quantities = {'original_healpixel'}
        for _, dataset in self._iter_native_dataset():
            for k, v in dataset.items():
                fields = _get_fits_data(v).dtype.fields
                for name, (dt, size) in _get_fits_data(v).dtype.fields.items():
                    if dt.shape:
                        for i in range(dt.shape[0]):
                            native_quantities.add((k, name, i))
                    else:
                        native_quantities.add((k, name))
            break
        return native_quantities


    def _iter_native_dataset(self, pre_filters=None):
        for i in self._healpixel_list:
            if pre_filters and not all(f[0](*([i]*(len(f)-1))) for f in pre_filters):
                continue

            fp = dict()
            for key, path in self._catalog_sub_dirs.items():
                try:
                    fp[key] = fits.open(os.path.join(path, self._filename_template.format(i)))
                except (IOError, OSError):
                    pass
            try:
                if all(k in fp for k in self._catalog_sub_dirs):
                    yield i, fp
            finally:
                for f in fp.values():
                    f.close()


    @staticmethod
    def _fetch_native_quantity(dataset, native_quantity):
        healpix, fits_data = dataset
        if native_quantity == 'original_healpixel':
            data = np.empty(_get_fits_data(fits_data.values()[0]).shape, np.int)
            data.fill(healpix)
            return data
        data =  _get_fits_data(fits_data[native_quantity[0]])[native_quantity[1]]
        if len(native_quantity) == 3:
            data = data[:,native_quantity[2]]
        return data

# Registers the reader
register_reader(BuzzardGalaxyCatalog)
