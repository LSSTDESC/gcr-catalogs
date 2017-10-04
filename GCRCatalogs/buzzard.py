"""
Buzzard galaxy catalog class.
"""
from __future__ import division, print_function
import os
import re
import numpy as np
from astropy.io import fits
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog
from .register import register_reader

__all__ = ['BuzzardGalaxyCatalog']


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
                       healpix_pixels=None,
                       high_res=False,
                       **kwargs):

        assert(os.path.isdir(catalog_root_dir)), 'Catalog directory {} does not exist'.format(catalog_root_dir)

        self._catalog_path_template = {k: os.path.join(catalog_root_dir, v) for k, v in catalog_path_template.items()}
        self._default_healpix_pixels = tuple(healpix_pixels or self._get_healpix_pixels())
        self.healpix_pixels = None
        self.reset_healpix_pixels()
        self.check_healpix_pixels()

        self._pre_filter_quantities = {'healpix_pixel'}

        self.cosmology = FlatLambdaCDM(**cosmology)
        self.halo_mass_def = halo_mass_def
        self.lightcone = bool(lightcone)

        _c = 299792.458
        _abs_mask_func = lambda x: np.where(x==99.0, np.nan, x + 5 * np.log10(self.cosmology.h))
        _mask_func = lambda x: np.where(x==99.0, np.nan, x)

        if high_res:
            print('Warning! high_res version has not been fully implemented')
            pass #TODO: add quantity modifiers

        else:
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

            for i, b in enumerate('grizY'):
                self._quantity_modifiers['Mag_true_{}_des_z01'.format(b)] = (_abs_mask_func, ('truth', 'AMAG', i))
                self._quantity_modifiers['Mag_true_{}_any'.format(b)] = (_abs_mask_func, ('truth', 'AMAG', i))
                self._quantity_modifiers['mag_{}_des'.format(b)] = (_mask_func, ('truth', 'OMAG', i))
                self._quantity_modifiers['mag_{}_any'.format(b)] = (_mask_func, ('truth', 'OMAG', i))
                self._quantity_modifiers['magerr_{}_des'.format(b)] = (_mask_func, ('truth', 'OMAGERR', i))
                self._quantity_modifiers['magerr_{}_any'.format(b)] = (_mask_func, ('truth', 'OMAGERR', i))


    def _get_healpix_pixels(self):
        try:
            path = self._catalog_path_template['truth']
        except KeyError:
            path = next(iter(self._catalog_path_template.values()))

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
        self.healpix_pixels = list(self._default_healpix_pixels)


    def _generate_native_quantity_list(self):
        native_quantities = {'healpix_pixel'}
        for _, dataset in self._iter_native_dataset():
            for k, v in dataset.items():
                for name, (dt, size) in v.dtype.fields.items():
                    if dt.shape:
                        for i in range(dt.shape[0]):
                            native_quantities.add((k, name, i))
                    else:
                        native_quantities.add((k, name))
            break
        return native_quantities


    def _iter_native_dataset(self, pre_filters=None):
        for i in self.healpix_pixels:
            args = dict(healpix_pixel=i)
            if pre_filters and not all(f[0](*(args[k] for k in f[1:])) for f in pre_filters):
                continue

            fp = list()
            fp_data = dict()
            try:
                for key, path in self._catalog_path_template.items():
                    fp_this = fits.open(path.format(i), mode='readonly', memmap=True, lazy_load_hdus=True)
                    fp.append(fp_this)
                    fp_data[key] = fp_this[1].data
                yield i, fp_data
            finally:
                del fp_data
                for f in fp:
                    f.close()
                    del f[1].data
                del fp


    @staticmethod
    def _fetch_native_quantity(dataset, native_quantity):
        healpix, fits_data = dataset
        if native_quantity == 'healpix_pixel':
            data = np.empty(fits_data.values()[0].shape, np.int)
            data.fill(healpix)
        elif len(native_quantity) == 2:
            data = fits_data[native_quantity[0]][native_quantity[1]]
        elif len(native_quantity) == 3:
            data = fits_data[native_quantity[0]][native_quantity[1]][:,native_quantity[2]]
        else:
            raise ValueError('something wrong with the native_quantity {}'.format(native_quantity))
        return data


# Registers the reader
register_reader(BuzzardGalaxyCatalog)
