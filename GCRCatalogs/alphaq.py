"""
Alpha Q galaxy catalog class.
"""
from __future__ import division
import os
import re
import warnings
import hashlib
from distutils.version import StrictVersion # pylint: disable=no-name-in-module,import-error
import numpy as np
import h5py
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog

__all__ = ['AlphaQGalaxyCatalog']
__version__ = '2.1.2'


def md5(fname, chunk_size=65536):
    """
    generate MD5 sum for *fname*
    """
    hash_md5 = hashlib.md5()
    with open(fname, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

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

class AlphaQGalaxyCatalog(BaseGenericCatalog):
    """
    Alpha Q galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, filename, **kwargs): # pylint: disable-msg=W0221

        assert os.path.isfile(filename), 'Catalog file {} does not exist'.format(filename)
        self._file = filename

        if kwargs.get('md5'):
            assert md5(self._file) == kwargs['md5'], 'md5 sum does not match!'
        else:
            warnings.warn('No md5 sum specified in the config file')

        self.lightcone = kwargs.get('lightcone')

        with h5py.File(self._file, 'r') as fh:
            # get version
            catalog_version = list()
            for version_label in ('Major', 'Minor', 'MinorMinor'):
                try:
                    catalog_version.append(fh['/metaData/version' + version_label].value)
                except KeyError:
                    break
            catalog_version = StrictVersion('.'.join(map(str, catalog_version or (2, 0))))

            # get cosmology
            self.cosmology = FlatLambdaCDM(
                H0=fh['metaData/simulationParameters/H_0'].value,
                Om0=fh['metaData/simulationParameters/Omega_matter'].value,
                Ob0=fh['metaData/simulationParameters/Omega_b'].value,
            )

            # get sky area
            if catalog_version >= StrictVersion("2.1.1"):
                self.sky_area = float(fh['metaData/skyArea'].value)
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
            'shear_2':       'shear2',
            'convergence':   'convergence',
            'magnification': 'magnification',
            'halo_id':       'hostIndex',
            'halo_mass':     'hostHaloMass',
            'is_central':    (lambda x: x.astype(np.bool), 'isCentral'),
            'stellar_mass':  'totalMassStellar',
            'stellar_mass_disk':        'diskMassStellar',
            'stellar_mass_bulge':       'spheroidMassStellar',
            'size_disk_true':           'morphology/diskMajorAxisArcsec',
            'size_bulge_true':          'morphology/spheroidMajorAxisArcsec',
            'size_minor_disk_true':     'morphology/diskMinorAxisArcsec',
            'size_minor_bulge_true':    'morphology/spheroidMinorAxisArcsec',
            'position_angle_true':      'morphology/positionAngle',
            'sersic_disk':              'morphology/diskSersicIndex',
            'sersic_bulge':             'morphology/spheroidSersicIndex',
            'ellipticity_true':         'morphology/totalEllipticity',
            'ellipticity_1_true':       'morphology/totalEllipticity1',
            'ellipticity_2_true':       'morphology/totalEllipticity2',
            'ellipticity_disk_true':         'morphology/diskEllipticity',
            'ellipticity_1_disk_true':       'morphology/diskEllipticity1',
            'ellipticity_2_disk_true':       'morphology/diskEllipticity2',
            'ellipticity_bulge_true':         'morphology/spheroidEllipticity',
            'ellipticity_1_bulge_true':       'morphology/spheroidEllipticity1',
            'ellipticity_2_bulge_true':       'morphology/spheroidEllipticity2',
            'size_true': (
                lambda size1, size2, lum1, lum2: ((size1*lum1)+(size2*lum2))/(lum1+lum2),
                'morphology/diskMajorAxisArcsec',
                'morphology/spheroidMajorAxisArcsec',
                'LSST_filters/diskLuminositiesStellar:LSST_r:rest',
                'LSST_filters/spheroidLuminositiesStellar:LSST_r:rest',
            ),
            'A_v' : (_calc_Av,
                    'otherLuminosities/totalLuminositiesStellar:V:rest',
                    'otherLuminosities/totalLuminositiesStellar:V:rest:dustAtlas',
              
            ),
            'R_v' : (_calc_Rv,
                    'otherLuminosities/totalLuminositiesStellar:V:rest',
                    'otherLuminosities/totalLuminositiesStellar:V:rest:dustAtlas',
                    'otherLuminosities/totalLuminositiesStellar:B:rest',
                    'otherLuminosities/totalLuminositiesStellar:B:rest:dustAtlas',

            ),
            'position_x': 'x',
            'position_y': 'y',
            'position_z': 'z',
            'velocity_x': 'vx',
            'velocity_y': 'vy',
            'velocity_z': 'vz',
        }

        # add magnitudes
        for band in 'ugrizY':
            if band != 'Y':
                self._quantity_modifiers['mag_{}_sdss'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band)
                self._quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest'.format(band)
            self._quantity_modifiers['mag_{}_lsst'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower())
            self._quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest'.format(band.lower())

        # add SEDs
        translate_component_name = {'total': '', 'disk': '_disk', 'spheroid': '_bulge'}
        sed_re = re.compile(r'^SEDs/([a-z]+)LuminositiesStellar:SED_(\d+)_(\d+):rest$')
        for quantity in self._native_quantities:
            m = sed_re.match(quantity)
            if m is None:
                continue
            component, start, width = m.groups()
            self._quantity_modifiers['sed_{}_{}{}'.format(start, width, translate_component_name[component])] = quantity

        # make quantity modifiers work in older versions
        if catalog_version < StrictVersion('2.1.2'):
            self._quantity_modifiers.update({
                'position_angle_true':     (lambda pos_angle: np.rad2deg(np.rad2deg(pos_angle)), 'morphology/positionAngle'), #I converted the units the wrong way, so a double conversion is required.
            })

        if catalog_version < StrictVersion('2.1.1'):
            self._quantity_modifiers.update({
                'disk_sersic_index':  'diskSersicIndex',
                'bulge_sersic_index': 'spheroidSersicIndex',
            })
            del self._quantity_modifiers['ellipticity_1']
            del self._quantity_modifiers['ellipticity_2']

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
        assert not native_filters, '*native_filters* is not supported'
        with h5py.File(self._file, 'r') as fh:
            def _native_quantity_getter(native_quantity):
                return fh['galaxyProperties/{}'.format(native_quantity)].value
            yield _native_quantity_getter



    def _get_native_quantity_info_dict(self, quantity, default=None):
        with h5py.File(self._file, 'r') as fh:
            quantity_key = 'galaxyProperties/' + quantity
            if quantity_key not in fh:
                return default
            modifier = lambda k, v: None if k == 'description' and v == b'None given' else v.decode()
            return {k: modifier(k, v) for k, v in fh[quantity_key].attrs.items()}



    def _get_quantity_info_dict(self, quantity, default=None):
        q_mod = self.get_quantity_modifier(quantity)
        if callable(q_mod) or (isinstance(q_mod, (tuple, list)) and len(q_mod) > 1 and callable(q_mod[0])):
            warnings.warn('This value is composed of a function on native quantities. So we have no idea what the units are')
            return default
        return self._get_native_quantity_info_dict(q_mod or quantity, default=default)

