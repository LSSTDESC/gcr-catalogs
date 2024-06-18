"""
Alpha Q galaxy catalog class.
"""
from __future__ import division
import os
import re
import warnings
from distutils.version import StrictVersion # pylint: disable=no-name-in-module,import-error
import numpy as np
import h5py
from GCR import BaseGenericCatalog
from .cosmology import FlatLambdaCDM
from .utils import md5, decode

__all__ = ['AlphaQGalaxyCatalog']
__version__ = '5.0.0'


def _calc_weighted_size(size1, size2, lum1, lum2):
    return ((size1*lum1) + (size2*lum2)) / (lum1+lum2)


def _calc_weighted_size_minor(size1, size2, lum1, lum2, ell):
    size = _calc_weighted_size(size1, size2, lum1, lum2)
    return size * (1.0 - ell) / (1.0 + ell)


def _calc_conv(mag, shear1, shear2):
    slct = mag < 0.2
    mag_corr = np.copy(mag)
    mag_corr[slct] = 1.0 # manually changing the values for when magnification is near zero.
    conv = 1.0 - np.sqrt(1.0/mag_corr + shear1**2 + shear2**2)
    return conv


def _calc_Rv(lum_v, lum_v_dust, lum_b, lum_b_dust):
    v = lum_v_dust/lum_v
    b = lum_b_dust/lum_b
    bv = b/v
    Rv = np.log10(v) / np.log10(bv)
    Rv[(v == 1) & (b == 1)] = 1.0
    Rv[v == b] = np.nan
    return Rv


def _calc_Av(lum_v, lum_v_dust):
    Av = -2.5*(np.log10(lum_v_dust/lum_v))
    Av[lum_v_dust == 0] = np.nan
    return Av


def _gen_position_angle(size_reference):
    # pylint: disable=protected-access
    size = size_reference.size
    if not hasattr(_gen_position_angle, "_pos_angle") or _gen_position_angle._pos_angle.size != size:
        _gen_position_angle._pos_angle = np.random.RandomState(123497).uniform(0, 180, size)
    return _gen_position_angle._pos_angle


def _calc_ellipticity_1(ellipticity):
    # position angle using ellipticity as reference for the size or
    # the array. The angle is converted from degrees to radians
    pos_angle = _gen_position_angle(ellipticity)*np.pi/180.0
    # use the correct conversion for ellipticity 1 from ellipticity
    # and position angle
    return ellipticity*np.cos(2.0*pos_angle)


def _calc_ellipticity_2(ellipticity):
    # position angle using ellipticity as reference for the size or
    # the array. The angle is converted from degrees to radians
    pos_angle = _gen_position_angle(ellipticity)*np.pi/180.0
    # use the correct conversion for ellipticity 2 from ellipticity
    # and position angle
    return ellipticity*np.sin(2.0*pos_angle)


def _gen_galaxy_id(size_reference):
    # pylint: disable=protected-access
    size = size_reference.size
    if not hasattr(_gen_galaxy_id, "_galaxy_id") or _gen_galaxy_id._galaxy_id.size != size:
        _gen_galaxy_id._galaxy_id = np.arange(size, dtype='i8')
    return _gen_galaxy_id._galaxy_id

def _calc_lensed_magnitude(magnitude, magnification):
    magnification[magnification==0]=1.0
    return magnitude -2.5*np.log10(magnification)

class AlphaQGalaxyCatalog(BaseGenericCatalog):
    """
    Alpha Q galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, filename, **kwargs): #pylint: disable=W0221

        if not os.path.isfile(filename):
            raise ValueError('Catalog file {} does not exist'.format(filename))
        self._file = filename

        if kwargs.get('md5'):
            if md5(self._file) != kwargs['md5']:
                raise ValueError('md5 sum does not match!')
        else:
            warnings.warn('No md5 sum specified in the config file')

        self.lightcone = kwargs.get('lightcone')

        with h5py.File(self._file, 'r') as fh:
            # get version
            catalog_version = list()
            for version_label in ('Major', 'Minor', 'MinorMinor'):
                try:
                    catalog_version.append(fh['/metaData/version' + version_label][()])
                except KeyError:
                    break
            catalog_version = StrictVersion('.'.join(map(str, catalog_version or (2, 0))))

            # get cosmology
            self.cosmology = FlatLambdaCDM(
                H0=fh['metaData/simulationParameters/H_0'][()],
                Om0=fh['metaData/simulationParameters/Omega_matter'][()],
                Ob0=fh['metaData/simulationParameters/Omega_b'][()],
            )
            self.cosmology.sigma8 = fh['metaData/simulationParameters/sigma_8'][()]
            self.cosmology.n_s = fh['metaData/simulationParameters/N_s'][()]
            self.halo_mass_def = fh['metaData/simulationParameters/haloMassDefinition'][()]

            # get sky area
            if catalog_version >= StrictVersion("2.1.1"):
                self.sky_area = float(fh['metaData/skyArea'][()])
            else:
                self.sky_area = 25.0 #If the sky area isn't specified use the default value of the sky area.

            # get native quantities
            self._native_quantities = set()
            def _collect_native_quantities(name, obj):
                if isinstance(obj, h5py.Dataset):
                    self._native_quantities.add(name)
            fh['galaxyProperties'].visititems(_collect_native_quantities)

        # check versions
        self.version = kwargs.get('version', '0.0.0')
        config_version = StrictVersion(self.version)
        if config_version != catalog_version:
            raise ValueError('Catalog file version {} does not match config version {}'.format(catalog_version, config_version))
        if StrictVersion(__version__) < config_version:
            raise ValueError('Reader version {} is less than config version {}'.format(__version__, catalog_version))

        self.catalog_version = catalog_version

        # specify quantity modifiers
        self._quantity_modifiers = {
            'galaxy_id' :    'galaxyID',
            'ra':            'ra',
            'dec':           'dec',
            'ra_true':       'ra_true',
            'dec_true':      'dec_true',
            'redshift':      'redshift',
            'redshift_true': 'redshiftHubble',
            'shear_1':       'shear1',
            'shear_2':       (np.negative, 'shear2'),
            'shear_2_treecorr': (np.negative, 'shear2'),
            'shear_2_phosim':   'shear2',
            'convergence': (
                _calc_conv,
                'magnification',
                'shear1',
                'shear2',
            ),
            'magnification': (lambda mag: np.where(mag < 0.2, 1.0, mag), 'magnification'),
            'halo_id':       'hostHaloTag',
            'halo_mass':     (lambda x: x/self.cosmology.h, 'hostHaloMass'),
            'is_central':    (lambda x: x.astype(bool), 'isCentral'),
            'stellar_mass':  'totalMassStellar',
            'stellar_mass_disk':        'diskMassStellar',
            'stellar_mass_bulge':       'spheroidMassStellar',
            'size_disk_true':           'morphology/diskMajorAxisArcsec',
            'size_bulge_true':          'morphology/spheroidMajorAxisArcsec',
            'size_minor_disk_true':     'morphology/diskMinorAxisArcsec',
            'size_minor_bulge_true':    'morphology/spheroidMinorAxisArcsec',
            'position_angle_true':      (_gen_position_angle, 'morphology/positionAngle'),
            'sersic_disk':              'morphology/diskSersicIndex',
            'sersic_bulge':             'morphology/spheroidSersicIndex',
            'ellipticity_true':         'morphology/totalEllipticity',
            'ellipticity_1_true':       (_calc_ellipticity_1, 'morphology/totalEllipticity'),
            'ellipticity_2_true':       (_calc_ellipticity_2, 'morphology/totalEllipticity'),
            'ellipticity_disk_true':    'morphology/diskEllipticity',
            'ellipticity_1_disk_true':  (_calc_ellipticity_1, 'morphology/diskEllipticity'),
            'ellipticity_2_disk_true':  (_calc_ellipticity_2, 'morphology/diskEllipticity'),
            'ellipticity_bulge_true':   'morphology/spheroidEllipticity',
            'ellipticity_1_bulge_true': (_calc_ellipticity_1, 'morphology/spheroidEllipticity'),
            'ellipticity_2_bulge_true': (_calc_ellipticity_2, 'morphology/spheroidEllipticity'),
            'size_true': (
                _calc_weighted_size,
                'morphology/diskMajorAxisArcsec',
                'morphology/spheroidMajorAxisArcsec',
                'LSST_filters/diskLuminositiesStellar:LSST_r:rest',
                'LSST_filters/spheroidLuminositiesStellar:LSST_r:rest',
            ),
            'size_minor_true': (
                _calc_weighted_size_minor,
                'morphology/diskMajorAxisArcsec',
                'morphology/spheroidMajorAxisArcsec',
                'LSST_filters/diskLuminositiesStellar:LSST_r:rest',
                'LSST_filters/spheroidLuminositiesStellar:LSST_r:rest',
                'morphology/totalEllipticity',
            ),
            'bulge_to_total_ratio_i': (
                lambda x, y: x/(x+y),
                'SDSS_filters/spheroidLuminositiesStellar:SDSS_i:observed',
                'SDSS_filters/diskLuminositiesStellar:SDSS_i:observed',
            ),
            'A_v': (
                _calc_Av,
                'otherLuminosities/totalLuminositiesStellar:V:rest',
                'otherLuminosities/totalLuminositiesStellar:V:rest:dustAtlas',
            ),
            'A_v_disk': (
                _calc_Av,
                'otherLuminosities/diskLuminositiesStellar:V:rest',
                'otherLuminosities/diskLuminositiesStellar:V:rest:dustAtlas',
            ),
            'A_v_bulge': (
                _calc_Av,
                'otherLuminosities/spheroidLuminositiesStellar:V:rest',
                'otherLuminosities/spheroidLuminositiesStellar:V:rest:dustAtlas',
            ),
            'R_v': (
                _calc_Rv,
                'otherLuminosities/totalLuminositiesStellar:V:rest',
                'otherLuminosities/totalLuminositiesStellar:V:rest:dustAtlas',
                'otherLuminosities/totalLuminositiesStellar:B:rest',
                'otherLuminosities/totalLuminositiesStellar:B:rest:dustAtlas',
            ),
            'R_v_disk': (
                _calc_Rv,
                'otherLuminosities/diskLuminositiesStellar:V:rest',
                'otherLuminosities/diskLuminositiesStellar:V:rest:dustAtlas',
                'otherLuminosities/diskLuminositiesStellar:B:rest',
                'otherLuminosities/diskLuminositiesStellar:B:rest:dustAtlas',
            ),
            'R_v_bulge': (
                _calc_Rv,
                'otherLuminosities/spheroidLuminositiesStellar:V:rest',
                'otherLuminosities/spheroidLuminositiesStellar:V:rest:dustAtlas',
                'otherLuminosities/spheroidLuminositiesStellar:B:rest',
                'otherLuminosities/spheroidLuminositiesStellar:B:rest:dustAtlas',
            ),
            'position_x': (lambda x: x/self.cosmology.h, 'x'),
            'position_y': (lambda x: x/self.cosmology.h, 'y'),
            'position_z': (lambda x: x/self.cosmology.h, 'z'),
            'velocity_x': 'vx',
            'velocity_y': 'vy',
            'velocity_z': 'vz',
        }

        # add magnitudes
        for band in 'ugrizyY':
            if band != 'y' and band != 'Y':
                self._quantity_modifiers['mag_{}_sdss'.format(band)] = (_calc_lensed_magnitude, 'SDSS_filters/magnitude:SDSS_{}:observed:dustAtlas'.format(band), 'magnification',)
                self._quantity_modifiers['mag_{}_sdss_no_host_extinction'.format(band)] = (_calc_lensed_magnitude, 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band), 'magnification',)
                self._quantity_modifiers['mag_true_{}_sdss'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed:dustAtlas'.format(band)
                self._quantity_modifiers['mag_true_{}_sdss_no_host_extinction'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band)
                self._quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest:dustAtlas'.format(band)
                self._quantity_modifiers['Mag_true_{}_sdss_z0_no_host_extinction'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest'.format(band)

            self._quantity_modifiers['mag_{}_lsst'.format(band)] = (_calc_lensed_magnitude, 'LSST_filters/magnitude:LSST_{}:observed:dustAtlas'.format(band.lower()), 'magnification',)
            self._quantity_modifiers['mag_{}_lsst_no_host_extinction'.format(band)] = (_calc_lensed_magnitude, 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower()), 'magnification',)
            self._quantity_modifiers['mag_true_{}_lsst'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed:dustAtlas'.format(band.lower())
            self._quantity_modifiers['mag_true_{}_lsst_no_host_extinction'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower())
            self._quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest:dustAtlas'.format(band.lower())
            self._quantity_modifiers['Mag_true_{}_lsst_z0_no_host_extinction'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest'.format(band.lower())

            if band != 'Y':
                self._quantity_modifiers['mag_{}'.format(band)] = self._quantity_modifiers['mag_{}_lsst'.format(band)]
                self._quantity_modifiers['mag_true_{}'.format(band)] = self._quantity_modifiers['mag_true_{}_lsst'.format(band)]


        # add SEDs
        translate_component_name = {'total': '', 'disk': '_disk', 'spheroid': '_bulge'}
        sed_re = re.compile(r'^SEDs/([a-z]+)LuminositiesStellar:SED_(\d+)_(\d+):rest((?::dustAtlas)?)$')
        for quantity in self._native_quantities:
            m = sed_re.match(quantity)
            if m is None:
                continue
            component, start, width, dust = m.groups()
            key = 'sed_{}_{}{}{}'.format(start, width, translate_component_name[component], '' if dust else '_no_host_extinction')
            self._quantity_modifiers[key] = quantity

        # make quantity modifiers work in older versions
        if catalog_version < StrictVersion('4.0'):
            self._quantity_modifiers.update({
                'galaxy_id' :    (_gen_galaxy_id, 'galaxyID'),
            })

        if catalog_version < StrictVersion('3.0'):
            self._quantity_modifiers.update({
                'galaxy_id' :    'galaxyID',
                'host_id': 'hostIndex',
                'position_angle_true':      'morphology/positionAngle',
                'ellipticity_1_true':       'morphology/totalEllipticity1',
                'ellipticity_2_true':       'morphology/totalEllipticity2',
                'ellipticity_1_disk_true':  'morphology/diskEllipticity1',
                'ellipticity_2_disk_true':  'morphology/diskEllipticity2',
                'ellipticity_1_bulge_true': 'morphology/spheroidEllipticity1',
                'ellipticity_2_bulge_true': 'morphology/spheroidEllipticity2',
                'halo_mass': 'hostHaloMass',
                'position_x': 'x',
                'position_y': 'y',
                'position_z': 'z',
            })

        if catalog_version < StrictVersion('2.1.2'):
            self._quantity_modifiers.update({
                'position_angle_true':     (lambda pos_angle: np.rad2deg(np.rad2deg(pos_angle)), 'morphology/positionAngle'), #I converted the units the wrong way, so a double conversion is required.
            })

        if catalog_version < StrictVersion('2.1.1'):
            self._quantity_modifiers.update({
                'sersic_disk':  'diskSersicIndex',
                'sersic_bulge': 'spheroidSersicIndex',
            })
            for key in (
                'size_minor_true',
                'ellipticity_true',
                'ellipticity_1_true',
                'ellipticity_2_true',
                'ellipticity_1_disk_true',
                'ellipticity_2_disk_true',
                'ellipticity_1_bulge_true',
                'ellipticity_2_bulge_true',
            ):
                if key in self._quantity_modifiers:
                    del self._quantity_modifiers[key]

        if catalog_version == StrictVersion('2.0'): # to be backward compatible
            self._quantity_modifiers.update({
                'ra':       (lambda x: x/3600, 'ra'),
                'ra_true':  (lambda x: x/3600, 'ra_true'),
                'dec':      (lambda x: x/3600, 'dec'),
                'dec_true': (lambda x: x/3600, 'dec_true'),
            })


    def _generate_native_quantity_list(self):
        return self._native_quantities


    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise ValueError('*native_filters* is not supported')
        with h5py.File(self._file, 'r') as fh:
            def _native_quantity_getter(native_quantity):
                return fh['galaxyProperties/{}'.format(native_quantity)][()]
            yield _native_quantity_getter


    def _get_native_quantity_info_dict(self, quantity, default=None):
        with h5py.File(self._file, 'r') as fh:
            quantity_key = 'galaxyProperties/' + quantity
            if quantity_key not in fh:
                return default
            modifier = lambda k, v: None if k == 'description' and decode(v) == 'None given' else decode(v)
            return_qty = {k: modifier(k, v) for k, v in fh[quantity_key].attrs.items()}
            # a hot fix of the units of native halo mass (hostHaloMass) and x for v3+
            if self.catalog_version >= StrictVersion('3.0') and quantity == 'hostHaloMass':
                return_qty['units'] = 'Msun/h'
            if self.catalog_version < StrictVersion('3.0') and quantity in set('xyz'):
                return_qty['units'] = 'comoving Mpc'
            return return_qty


    def _get_quantity_info_dict(self, quantity, default=None):
        q_mod = self.get_quantity_modifier(quantity)
        if callable(q_mod) or (isinstance(q_mod, (tuple, list)) and len(q_mod) > 1 and callable(q_mod[0])):
            warnings.warn('This value is composed of a function on native quantities. So we have no idea what the units are')
            return default
        return self._get_native_quantity_info_dict(q_mod or quantity, default=default)
