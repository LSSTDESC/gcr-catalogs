"""
CosmoDC2 galaxy catalog class.
"""
from __future__ import division
import os
import re
import warnings
from distutils.version import StrictVersion # pylint: disable=no-name-in-module,import-error
import numpy as np
import h5py
from astropy.cosmology import FlatLambdaCDM
from GCR import BaseGenericCatalog

__all__ = ['CosmoDC2GalaxyCatalog', 'UMGalaxyCatalog']
__version__ = '1.0.0'


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

def _calc_mag(conv, shear1, shear2):
    mag = 1.0/((1.0 - conv)**2 - shear1**2 - shear2**2)
    return mag

def _calc_Rv(lum_v, lum_v_dust, lum_b, lum_b_dust):
    with np.errstate(divide='ignore', invalid='ignore'):
        v = lum_v_dust/lum_v
        b = lum_b_dust/lum_b
        bv = b/v
        Rv = np.log10(v) / np.log10(bv)
        Rv[(v == 1) & (b == 1)] = 1.0
        Rv[v == b] = np.nan
        return Rv


def _calc_Av(lum_v, lum_v_dust):
    with np.errstate(divide='ignore', invalid='ignore'):
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


def _calc_lensed_magnitude(magnitude, magnification):
    magnification[magnification == 0] = 1.0
    return magnitude -2.5*np.log10(magnification)


class BaseCosmoDC2Catalog(BaseGenericCatalog):
    """
    BaseCosmoDC2Catalog class for catalogs that have cosmoDC-like structures.
    """

    def _subclass_init(self, catalog_root_dir, catalog_path_template, cosmology, healpix_pixels=None, zlo=None, zhi=None, check_file_metadata=False, **kwargs):
        # pylint: disable=W0221
        if not os.path.isdir(catalog_root_dir):
            raise ValueError('Catalog directory {} does not exist'.format(catalog_root_dir))

        self._catalog_path_template = os.path.join(catalog_root_dir, catalog_path_template)
        self._native_filter_quantities = {'healpix_pixel', 'redshift_block_lower'}
        self._default_zrange_lo, self._default_zrange_hi, self._default_healpix_pixels = self._get_healpix_info()
        self.zrange_lo = self._default_zrange_lo if zlo is None else zlo
        self.zrange_hi = self._default_zrange_hi if zhi is None else zhi
        self.healpix_pixels = self._default_healpix_pixels if healpix_pixels is None else healpix_pixels
        self.healpix_pixel_files = self._get_healpix_file_list(assert_files_complete=kwargs.get('assert_files_complete', True))

        cosmo_astropy_allowed = FlatLambdaCDM.__init__.__code__.co_varnames[1:]
        cosmo_astropy = {k: v for k, v in cosmology.items() if k in cosmo_astropy_allowed}
        self.cosmology = FlatLambdaCDM(**cosmo_astropy)
        for k, v in cosmology.items():
            if k not in cosmo_astropy_allowed:
                setattr(self.cosmology, k, v)

        self.version = kwargs.get('version', '0.0.0')
        self.lightcone = kwargs.get('lightcone', True)

        #get sky area and check files if requested
        self.sky_area = self._get_skyarea_info()
        if check_file_metadata:
            for healpix_file in self.healpix_pixel_files:
                self._check_file_metadata(healpix_file)

        self._native_quantities = set()
        self._native_quantities = set(self._generate_native_quantity_list())
        self._quantity_modifiers = self._generate_quantity_modifiers()

    def _get_group_names(self, fh): # pylint: disable=W0613
        return ['galaxyProperties']

    def _generate_native_quantity_list(self):
        if not self._native_quantities:
            filename = self.healpix_pixel_files[0]
            with h5py.File(filename, 'r') as fh:
                def _collect_native_quantities(name, obj):
                    if isinstance(obj, h5py.Dataset):
                        self._native_quantities.add(name)
                fh[self._get_group_names(fh)[0]].visititems(_collect_native_quantities)

        return self._native_quantities

    @staticmethod
    def _generate_quantity_modifiers():
        return {}

    def _get_healpix_info(self):
        path = self._catalog_path_template
        fname_pattern = os.path.basename(path).format(r'\d', r'\d', r'\d+')
        path = os.path.dirname(path)
        pattern = re.compile(r'\d+')
        if not os.listdir(path):
            raise ValueError('Problem with yaml file: no files with format {} found in {}'.format(fname_pattern, path))

        healpix_pixels = set()
        zvalues = set()
        for f in sorted(os.listdir(path)):
            m = re.match(fname_pattern, f)
            if m is not None:
                healpix_name = os.path.splitext(m.group())[0]
                zlo, zhi, hpx = pattern.findall(healpix_name)[-3:]
                healpix_pixels.add(int(hpx))
                zvalues.add(int(zlo))
                zvalues.add(int(zhi))

        return min(zvalues), max(zvalues), list(healpix_pixels)


    def _get_healpix_file_list(self, assert_files_complete=True):
        possible_healpix_pixel_files = [self._catalog_path_template.format(z, z+1, h) for z in range(self.zrange_lo, self.zrange_hi) for h in self.healpix_pixels]
        healpix_pixel_files = [f for f in possible_healpix_pixel_files if os.path.isfile(f)]
        if assert_files_complete and len(healpix_pixel_files) != len(possible_healpix_pixel_files):
            raise ValueError('Missing some catalog files: {}'.format(', '.join([f for f in possible_healpix_pixel_files if f not in healpix_pixel_files])))
        return healpix_pixel_files


    def _check_file_metadata(self, healpix_file, tol=1e-4):
        fh = h5py.File(healpix_file, 'r')
        try:
            # pylint: disable=E1101
            catalog_version = list()
            for version_label in ('Major', 'Minor', 'MinorMinor'):
                try:
                    catalog_version.append(fh['/metaData/version' + version_label].value)
                except KeyError:
                    break
            catalog_version = StrictVersion('.'.join(map(str, catalog_version or (0, 0))))

            #check cosmology
            metakeys = fh['metaData'].keys()
            if 'H_0' in metakeys and 'Omega_matter' in metakeys and 'Omega_b' in metakeys:
                H0 = fh['metaData/H_0'].value
                Om0 = fh['metaData/Omega_matter'].value
                Ob0 = fh['metaData/Omega_b'].value
                if  abs(H0 - self.cosmology.H0.value) > tol or abs(Om0 - self.cosmology.Om0) > tol or abs(Ob0 - self.cosmology.Ob0) > tol:
                    raise ValueError('Mismatch in cosmological parameters (H0:{}, Om0:{}, Ob0:{}) for healpix file {}'.format(H0, Om0, Ob0, healpix_file))

            # check versions
            config_version = StrictVersion(self.version)
            if config_version != catalog_version:
                raise ValueError('Catalog file version {} does not match config version {}'.format(catalog_version, config_version))
            if StrictVersion(__version__) < config_version:
                raise ValueError('Reader version {} is less than config version {}'.format(__version__, catalog_version))
        finally:
            fh.close()


    def _get_skyarea_info(self):
        skyarea = {}
        pattern = re.compile(r'\d+')
        for healpix_file in self.healpix_pixel_files:
            # pylint: disable=E1101
            try:
                fh = h5py.File(healpix_file, 'r')
            except:
                raise ValueError('Unable to read file {}'.format(healpix_file))
            healpix_name = os.path.splitext(os.path.basename(healpix_file))[0]
            zlo, zhi, hpx = pattern.findall(healpix_name)[-3:]
            if hpx not in skyarea:
                skyarea[hpx] = {}
            try:
                skyarea[hpx][zlo+'_'+zhi] = float(fh['metaData/skyArea'].value)
            except KeyError:
                skyarea[hpx][zlo+'_'+zhi] = np.rad2deg(np.rad2deg(4.0*np.pi/768.))
            fh.close()

        sky_area = 0.0
        for hpx in skyarea:
            sky_area = sky_area + max([skyarea[hpx][z] for z in skyarea[hpx]])

        return sky_area


    def _iter_native_dataset(self, native_filters=None):
        for healpix in self.healpix_pixels:

            if native_filters is not None and not native_filters.check_scalar({
                    'healpix_pixel': healpix,
            }):
                continue

            for zlo in range(self.zrange_lo, self.zrange_hi):

                if native_filters is not None and not native_filters.check_scalar({
                        'healpix_pixel': healpix,
                        'redshift_block_lower': zlo,
                }):
                    continue

                healpix_file = self._catalog_path_template.format(zlo, zlo+1, healpix)
                try:
                    with h5py.File(healpix_file, 'r') as fh:
                        for group in self._get_group_names(fh):
                            # pylint: disable=E1101,W0640
                            yield lambda native_quantity: fh['{}/{}'.format(group, native_quantity)].value

                except (IOError, OSError):
                    print('Cannot open file {}'.format(healpix_file))


    def _get_native_quantity_info_dict(self, quantity, default=None):
        #use first file in list to get information
        filename = self._catalog_path_template.format(self.zrange_lo, self.zrange_lo+1, self.healpix_pixels[0])
        with h5py.File(filename, 'r') as fh:
            quantity_key = '{}/{}'.format(self._get_group_names(fh)[0], quantity) #use first lc shell
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



class CosmoDC2GalaxyCatalog(BaseCosmoDC2Catalog):
    """
    CosmoDC2 galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
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
            'halo_id':       'uniqueHaloID',
            'halo_mass':     'hostHaloMass',
            'is_central':    (lambda x: x.astype(np.bool), 'isCentral'),
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
            'position_x': 'x',
            'position_y': 'y',
            'position_z': 'z',
            'velocity_x': 'vx',
            'velocity_y': 'vy',
            'velocity_z': 'vz',
        }

        # add magnitudes
        for band in 'ugrizyY':
            if band != 'y' and band != 'Y':
                quantity_modifiers['mag_true_{}_sdss'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed:dustAtlas'.format(band)
                quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest:dustAtlas'.format(band)
                quantity_modifiers['mag_true_{}_sdss_no_host_extinction'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band)
                quantity_modifiers['Mag_true_{}_sdss_z0_no_host_extinction'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest'.format(band)
            quantity_modifiers['mag_true_{}_lsst'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed:dustAtlas'.format(band.lower())
            quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest:dustAtlas'.format(band.lower())
            quantity_modifiers['mag_true_{}_lsst_no_host_extinction'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower())
            quantity_modifiers['Mag_true_{}_lsst_z0_no_host_extinction'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest'.format(band.lower())

        # add lensed magnitudes
        for band in 'ugrizyY':
            if band != 'y' and band != 'Y':
                quantity_modifiers['mag_{}_sdss'.format(band)] = (_calc_lensed_magnitude, 'SDSS_filters/magnitude:SDSS_{}:observed:dustAtlas'.format(band), 'magnification',)
                quantity_modifiers['mag_{}_sdss_no_host_extinction'.format(band)] = (_calc_lensed_magnitude, 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band), 'magnification',)
            quantity_modifiers['mag_{}_lsst'.format(band)] = (_calc_lensed_magnitude, 'LSST_filters/magnitude:LSST_{}:observed:dustAtlas'.format(band.lower()), 'magnification',)
            quantity_modifiers['mag_{}_lsst_no_host_extinction'.format(band)] = (_calc_lensed_magnitude, 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower()), 'magnification',)

        # add SEDs
        translate_component_name = {'total': '', 'disk': '_disk', 'spheroid': '_bulge'}
        sed_re = re.compile(r'^SEDs/([a-z]+)LuminositiesStellar:SED_(\d+)_(\d+):rest((?::dustAtlas)?)$')
        for quantity in self._native_quantities:
            m = sed_re.match(quantity)
            if m is None:
                continue
            component, start, width, dust = m.groups()
            key = 'sed_{}_{}{}{}'.format(start, width, translate_component_name[component], '' if dust else '_no_host_extinction')
            quantity_modifiers[key] = quantity

        #FIXME: remove this section when these native quantity really exist.
        self._native_quantities.difference_update(set(q for q in self._native_quantities if (
            q.startswith('emissionLines/') or q.endswith('ContinuumLuminosity')
        )))

        catalog_version = StrictVersion(self.version)
        # make quantity modifiers work in older versions
        if catalog_version < StrictVersion('1.0'):
            quantity_modifiers['halo_id'] = 'UMachineNative/halo_id'

        # make quantity modifiers work in older versions
        if catalog_version < StrictVersion('0.2'):
            quantity_modifiers['halo_id'] = 'hostHaloTag'

        return quantity_modifiers


class UMGalaxyCatalog(BaseCosmoDC2Catalog):
    """
    UM galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """
    def _get_group_names(self, fh):
        return [k for k in fh if k.isdigit()]

    @staticmethod
    def _generate_quantity_modifiers():
        quantity_modifiers = {
            'galaxy_id' :    'galaxy_id',
            'ra_true':       'ra',
            'dec_true':      'dec',
            'redshift_true': 'redshift',
            'halo_id':       'target_halo_id',
            'halo_mass':     'target_halo_mass',
            'stellar_mass':  'obs_sm',
            'position_x': 'x',
            'position_y': 'y',
            'position_z': 'z',
            'velocity_x': 'vx',
            'velocity_y': 'vy',
            'velocity_z': 'vz',
            'is_central': (lambda x: x == -1, 'upid'),
        }

        # add magnitudes
        for band in 'gri':
            quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'restframe_extincted_sdss_abs_mag{}'.format(band)
            quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'restframe_extincted_sdss_abs_mag{}'.format(band)

        return quantity_modifiers


class UMShearCatalog(UMGalaxyCatalog):
    """
    UM shear catalog class.
    """
    @staticmethod
    def _generate_quantity_modifiers():
        quantity_modifiers = {
            'ra': 'ra_lensed',
            'dec': 'dec_lensed',
            'convergence': 'conv', 
            'magnification': (
                _calc_mag,
                'conv',
                'shear_1',
                'shear_2',
            ),
            'shear_2_treecorr': 'shear_2',
            'shear_2_phosim':   (np.negative, 'shear_2'),
            'shear_1':   'shear_1',
        }
        return quantity_modifiers
