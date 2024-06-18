"""
Buzzard galaxy catalog class.
"""
from __future__ import division, print_function
import os
import re
import functools
import numpy as np
from astropy.io import fits
from GCR import BaseGenericCatalog
from .cosmology import FlatLambdaCDM

__all__ = ['BuzzardGalaxyCatalog']


def _ellip2pa(e1, e2):
    return np.remainder(np.rad2deg(np.arctan2(e2, e1)/2.0), 180.0)


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


class BuzzardGalaxyCatalog(BaseGenericCatalog):
    """
    Buzzard galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self,
                       catalog_root_dir,
                       catalog_path_template,
                       cosmology,
                       halo_mass_def='vir',
                       lightcone=True,
                       sky_area=None,
                       healpix_pixels=None,
                       high_res=False,
                       use_cache=True,
                       **kwargs): #pylint: disable=W0221

        assert(os.path.isdir(catalog_root_dir)), 'Catalog directory {} does not exist'.format(catalog_root_dir)

        self._catalog_path_template = {k: os.path.join(catalog_root_dir, v) for k, v in catalog_path_template.items()}
        self._default_subset = 'truth' if 'truth' in self._catalog_path_template else next(iter(self._catalog_path_template.keys()))

        self._default_healpix_pixels = tuple(healpix_pixels or self._get_healpix_pixels())
        self.healpix_pixels = None
        self.reset_healpix_pixels()
        self.check_healpix_pixels()
        self._native_filter_quantities = {'healpix_pixel'}

        self.cache = dict() if use_cache else None

        self.cosmology = FlatLambdaCDM(**cosmology)
        self.halo_mass_def = halo_mass_def
        self.lightcone = bool(lightcone)
        self.sky_area  = float(sky_area or np.nan)
        self.version = kwargs.get('version', '0.0.0')

        _c = 299792.458
        _abs_mask_func = lambda x: np.where(x==99.0, np.nan, x + 5 * np.log10(self.cosmology.h))
        _mask_func = lambda x: np.where(x==99.0, np.nan, x)

        if high_res:
            self._quantity_modifiers = {
                'redshift': 'truth/Z',
                'ra_true': 'truth/RA',
                'dec_true': 'truth/DEC',
                'redshift_true' : (lambda zt, x, y, z, vx, vy, vz: zt - (x*vx+y*vy+z*vz)/np.sqrt(x*x+y*y+z*z)/_c,
                                   'truth/Z', 'truth/PX', 'truth/PY', 'truth/PZ', 'truth/VX', 'truth/VY', 'truth/VZ'),
                'halo_id': 'truth/HALOID',
                'halo_mass': (lambda x: x/self.cosmology.h, 'truth/M200'),
                'is_central': (lambda x: x.astype(bool), 'truth/CENTRAL'),
                'ellipticity_1_true': 'truth/TE/0',
                'ellipticity_2_true': 'truth/TE/1',
                'ellipticity_true': (np.hypot, 'truth/TE/0', 'truth/TE/1'),
                'position_angle_true': (_ellip2pa, 'truth/TE/0', 'truth/TE/1'),
                'size_true': 'truth/TSIZE',
                'position_x': (lambda x: x/self.cosmology.h, 'truth/PX'),
                'position_y': (lambda x: x/self.cosmology.h, 'truth/PY'),
                'position_z': (lambda x: x/self.cosmology.h, 'truth/PZ'),
                'velocity_x': 'truth/VX',
                'velocity_y': 'truth/VY',
                'velocity_z': 'truth/VZ',
            }

            for i, b in enumerate('ugrizyY'):
                if b == 'Y':
                    i -= 1
                self._quantity_modifiers['Mag_true_{}_lsst_z0'.format(b)] = (_abs_mask_func, 'lsst/AMAG/{}'.format(i))
                self._quantity_modifiers['mag_{}_lsst'.format(b)] = (_mask_func, 'lsst/OMAG/{}'.format(i))
                if b != 'y' and b != 'Y':
                    self._quantity_modifiers['Mag_true_{}_sdss_z01'.format(b)] = (_abs_mask_func, 'truth/AMAG/{}'.format(i))
                    self._quantity_modifiers['mag_true_{}_stripe82'.format(b)] = (_mask_func, 'stripe82/TMAG/{}'.format(i))
                    self._quantity_modifiers['mag_{}_stripe82'.format(b)] = (_mask_func, 'stripe82/OMAG/{}'.format(i))
                    self._quantity_modifiers['magerr_{}_stripe82'.format(b)] = (_mask_func, 'stripe82/OMAGERR/{}'.format(i))
                if b != 'u':
                    i -= 1
                    self._quantity_modifiers['Mag_true_{}_des_z01'.format(b)] = (_abs_mask_func, 'desy5/AMAG/{}'.format(i))
                    self._quantity_modifiers['mag_true_{}_des'.format(b)] = (_mask_func, 'desy5/TMAG/{}'.format(i))
                    self._quantity_modifiers['mag_{}_des'.format(b)] = (_mask_func, 'desy5/OMAG/{}'.format(i))
                    self._quantity_modifiers['magerr_{}_des'.format(b)] = (_mask_func, 'desy5/OMAGERR/{}'.format(i))

            for i, b in enumerate('ZYJHK'):
                self._quantity_modifiers['Mag_true_{}_vista_z01'.format(b)] = (_abs_mask_func, 'vista/AMAG/{}'.format(i))
                self._quantity_modifiers['mag_{}_vista'.format(b)] = (_mask_func, 'vista/OMAG/{}'.format(i))

            for i, b in enumerate(['acsf435w', 'acsf606w', 'acsf775w', 'acsf814w', 'acsf850lp', 'wfc3f275w', 'wfc3f336w',
                                   'wfc3f336w', 'wfc3f125w', 'wfc3f160w']):

                self._quantity_modifiers['Mag_true_{}_candels_z0'.format(b)] = (_abs_mask_func, 'candels/AMAG/{}'.format(i))
                self._quantity_modifiers['mag_{}_candels'.format(b)] = (_mask_func, 'candels/OMAG/{}'.format(i))

            for i, b in enumerate(['W1', 'W2', 'W3', 'W4']):
                self._quantity_modifiers['Mag_true_{}_wise_z0'.format(b)] = (_abs_mask_func, 'wise/AMAG/{}'.format(i))
                self._quantity_modifiers['mag_{}_wise'.format(b)] = (_mask_func, 'wise/OMAG/{}'.format(i))

            for i, b in enumerate(['1234']):
                self._quantity_modifiers['Mag_true_{}_irac_z0'.format(b)] = (_abs_mask_func, 'irac/AMAG/{}'.format(i))
                self._quantity_modifiers['mag_{}_irac'.format(b)] = (_mask_func, 'irac/OMAG/{}'.format(i))

        else:  # for regular (not high-res) buzzard (v1.6, v1.9.2, v2.0.0 etc)
            self._quantity_modifiers = {
                'galaxy_id': 'truth/ID',
                'redshift': (lambda zt, x, y, z, vx, vy, vz: zt + (x*vx+y*vy+z*vz)/np.sqrt(x*x+y*y+z*z)/_c,
                             'truth/Z', 'truth/PX', 'truth/PY', 'truth/PZ', 'truth/VX', 'truth/VY', 'truth/VZ'),
                'redshift_true': 'truth/Z',
                'ra': 'truth/RA',
                'dec': 'truth/DEC',
                'ra_true': 'truth/TRA',
                'dec_true': 'truth/TDEC',
                'halo_id': 'truth/HALOID',
                'halo_mass': (lambda x: x/self.cosmology.h, 'truth/M200'),
                'is_central': (lambda x: x.astype(bool), 'truth/CENTRAL'),
                'ellipticity_1': 'truth/EPSILON/0',
                'ellipticity_2': 'truth/EPSILON/1',
                'ellipticity': (np.hypot, 'truth/EPSILON/0', 'truth/EPSILON/1'),
                'position_angle': (_ellip2pa, 'truth/EPSILON/0', 'truth/EPSILON/1'),
                'ellipticity_1_true': 'truth/TE/0',
                'ellipticity_2_true': 'truth/TE/1',
                'ellipticity_true': (np.hypot, 'truth/TE/0', 'truth/TE/1'),
                'position_angle_true': (_ellip2pa, 'truth/TE/0', 'truth/TE/1'),
                'size': 'truth/SIZE',
                'size_true': 'truth/TSIZE',
                'shear_1': 'truth/GAMMA1',
                'shear_2': (np.negative, 'truth/GAMMA2'),
                'shear_2_treecorr': (np.negative, 'truth/GAMMA2'),
                'shear_2_phosim':   'truth/GAMMA2',
                'convergence': 'truth/KAPPA',
                'magnification': 'truth/MU',
                'position_x': (lambda x: x/self.cosmology.h, 'truth/PX'),
                'position_y': (lambda x: x/self.cosmology.h, 'truth/PY'),
                'position_z': (lambda x: x/self.cosmology.h, 'truth/PZ'),
                'velocity_x': 'truth/VX',
                'velocity_y': 'truth/VY',
                'velocity_z': 'truth/VZ',
            }

            for i, b in enumerate('grizY'):
                self._quantity_modifiers['mag_{}_des'.format(b)] = (_mask_func, 'truth/OMAG/{}'.format(i))
                self._quantity_modifiers['magerr_{}_des'.format(b)] = (_mask_func, 'truth/OMAGERR/{}'.format(i))
                self._quantity_modifiers['mag_true_{}_des'.format(b)] = (_mask_func, 'truth/TMAG/{}'.format(i))
                self._quantity_modifiers['Mag_true_{}_des_z01'.format(b)] = (_abs_mask_func, 'truth/AMAG/{}'.format(i))

            if not self.version.startswith('1.6'):  # for v1.9.2 and above
                for i, b in enumerate(['Z_vista', 'Y_vista', 'J_vista', 'H_vista', 'Ks_vista', 'u_lsst',
                                       'g_lsst', 'r_lsst', 'i_lsst', 'z_lsst', 'y_lsst', 'Y_wfirst',
                                       'J_wfirst', 'H_wfirst', 'K_wfirst']):
                    i += 6
                    self._quantity_modifiers['Mag_true_{}_z0'.format(b)] = (_abs_mask_func, 'auxmag/AMAG/{}'.format(i))
                    self._quantity_modifiers['mag_true_{}'.format(b)] = (_mask_func, 'auxmag/TMAG/{}'.format(i))
                    self._quantity_modifiers['mag_{}'.format(b)] = (_mask_func, 'auxmag/LMAG/{}'.format(i))

        # for all, aliasing the lsst filters
        for key in list(self._quantity_modifiers):
            if key.startswith('mag_') and key.endswith('_lsst'):
                self._quantity_modifiers[key[:-5]] = self._quantity_modifiers[key]

    def _get_healpix_pixels(self):
        path = self._catalog_path_template[self._default_subset]
        fname_pattern = re.escape(os.path.basename(path)).replace(r'\{', '{').replace(r'\}', '}').format(r'(\d+)')
        path = os.path.dirname(path)
        healpix_pixels = list()
        for f in os.listdir(path):
            m = re.match(fname_pattern, f)
            if m is not None:
                healpix_pixels.append(int(m.groups()[0]))
        healpix_pixels.sort()
        return healpix_pixels


    def check_healpix_pixels(self):
        assert all(os.path.isfile(path.format(i)) for path in self._catalog_path_template.values() for i in self.healpix_pixels)


    def reset_healpix_pixels(self):
        """
        Reset the list of healpixels used by the reader.
        """
        self.healpix_pixels = list(self._default_healpix_pixels) #pylint: disable=W0201


    def _generate_native_quantity_list(self):
        native_quantities = {'healpix_pixel'}
        healpix = next(iter(self.healpix_pixels))
        for subset in self._catalog_path_template.keys():
            f = self._open_dataset(healpix, subset)
            for name, (dt, _) in f.data.dtype.fields.items():
                if dt.shape:
                    for i in range(dt.shape[0]):
                        native_quantities.add('/'.join((subset, name, str(i))))
                else:
                    native_quantities.add('/'.join((subset, name)))
        return native_quantities


    def _iter_native_dataset(self, native_filters=None):
        for healpix in self.healpix_pixels:
            if native_filters is None or native_filters.check_scalar({'healpix_pixel': healpix}):
                yield functools.partial(self._native_quantity_getter, healpix=healpix)


    def _open_dataset(self, healpix, subset):
        path = self._catalog_path_template[subset].format(healpix)

        if self.cache is None:
            return FitsFile(path)

        key = (healpix, subset)
        if key not in self.cache:
            self.cache[key] = FitsFile(path)
        return self.cache[key]


    def _native_quantity_getter(self, native_quantity, healpix):
        if native_quantity == 'healpix_pixel':
            data = np.empty(self._open_dataset(healpix, self._default_subset).data.shape, int)
            data.fill(healpix)
            return data

        native_quantity = native_quantity.split('/')
        assert len(native_quantity) in {2,3}, 'something wrong with the native_quantity {}'.format(native_quantity)
        subset = native_quantity.pop(0)
        column = native_quantity.pop(0)
        data = self._open_dataset(healpix, subset).data[column]
        if native_quantity:
            data = data[:,int(native_quantity.pop(0))]
        return data.byteswap().newbyteorder()
