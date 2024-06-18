"""
CosmoDC2 galaxy catalog class.
"""
from __future__ import division
import os
import re
from itertools import product
from functools import partial
import warnings
from distutils.version import StrictVersion # pylint: disable=no-name-in-module,import-error
import yaml
import numpy as np
import h5py
import healpy as hp
from GCR import BaseGenericCatalog
from .cosmology import FlatLambdaCDM
from .utils import md5, first, decode

__all__ = ['CosmoDC2GalaxyCatalog', 'BaseDC2GalaxyCatalog', 'BaseDC2SnapshotGalaxyCatalog',
           'BaseDC2ShearCatalog', 'CosmoDC2AddonCatalog', 'SkySim5000GalaxyCatalog',
           'DiffSkyGalaxyCatalog']
__version__ = '3.1.0'

CHECK_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'catalog_configs/_cosmoDC2_check.yaml')

def _calc_weighted_size(size1, size2, lum1, lum2):
    return ((size1*lum1) + (size2*lum2)) / (lum1+lum2)


def _calc_weighted_size_minor(size1, size2, lum1, lum2, ell):
    size = _calc_weighted_size(size1, size2, lum1, lum2)
    return size * (1.0 - ell) / (1.0 + ell)


def _calc_mag(conv, shear1, shear2):
    mag = 1.0/((1.0 - conv)**2 - shear1**2 - shear2**2)
    return mag


def _calc_Rv(lum_v, lum_v_dust, lum_b, lum_b_dust): #Rv definition with best behavior
    with np.errstate(divide='ignore', invalid='ignore'):
        Av = -2.5*np.log10(lum_v_dust) + 2.5*np.log10(lum_v)
        Ab = -2.5*np.log10(lum_b_dust) + 2.5*np.log10(lum_b)
        Ebv = -2.5*np.log10(lum_b_dust) + 2.5*np.log10(lum_b) - 2.5*np.log10(lum_v_dust) + 2.5*np.log10(lum_v)
        Rv = Av / Ebv
        Rv[(Av == 0) & (Ab == 0)] = 1.0
        #remove remaining nans and infs for image sims
        mask = np.isfinite(Rv)
        r = np.random.RandomState(43) # for reproduceability
        Rv[~mask] = r.uniform(1.0, 5.0, np.count_nonzero(~mask))
        return Rv


def _calc_Av(lum_v, lum_v_dust):
    with np.errstate(divide='ignore', invalid='ignore'):
        Av = -2.5*(np.log10(lum_v_dust/lum_v))
        return Av


def _gen_position_angle(size_reference):
    # pylint: disable=protected-access
    size = size_reference.size
    if not hasattr(_gen_position_angle, "_pos_angle") or _gen_position_angle._pos_angle.size != size:
        _gen_position_angle._pos_angle = np.random.RandomState(123497).uniform(0, 180, size)
    return _gen_position_angle._pos_angle

def _calc_ellipticity_1_dc2(ellipticity):
    # position angle using ellipticity as reference for the size or
    # the array. The angle is converted from degrees to radians
    pos_angle = _gen_position_angle(ellipticity)*np.pi/180.0
    # use the correct conversion for ellipticity 1 from ellipticity
    # and position angle
    return ellipticity*np.cos(2.0*pos_angle)


def _calc_ellipticity_2_dc2(ellipticity):
    # position angle using ellipticity as reference for the size or
    # the array. The angle is converted from degrees to radians
    pos_angle = _gen_position_angle(ellipticity)*np.pi/180.0
    # use the correct conversion for ellipticity 2 from ellipticity
    # and position angle
    return ellipticity*np.sin(2.0*pos_angle)


def _calc_ellipticity_1(ellipticity, pos_angle):
    # convert to treecorr convention and from deg to radians
    pos_angle = np.negative(pos_angle)*np.pi/180.0
    return ellipticity*np.cos(2.0*pos_angle)


def _calc_ellipticity_2(ellipticity, pos_angle):
    # convert to treecorr convention and from deg to radians
    pos_angle = np.negative(pos_angle)*np.pi/180.0
    return ellipticity*np.sin(2.0*pos_angle)


def _limit_magnification(mag):
    mag = np.where(mag < 0.2, 1.0, mag)
    mag = np.where(mag > 2.0, 1.0, mag)
    return mag


def _calc_lensed_magnitude(magnitude, magnification):
    magnification[magnification == 0] = 1.0
    return magnitude -2.5*np.log10(magnification)


def _calc_lensed_magnitude_with_limits(magnitude, magnification):
    magnification = _limit_magnification(magnification)
    return magnitude -2.5*np.log10(magnification)


def _add_to_native_quantity_collector(name, obj, collector):
    if isinstance(obj, h5py.Dataset):
        collector.add(name)


class CosmoDC2ParentClass(BaseGenericCatalog):
    """
    CosmoDC2ParentClass: the parent class for
    CosmoDC2GalaxyCatalog, BaseDC2GalaxyCatalog, BaseDC2ShearCatalog,
    SkySim5000GalaxyCatalog and DiffSkyGalaxyCatalog
    """

    def _subclass_init(self, catalog_root_dir, catalog_filename_template, **kwargs):
        # pylint: disable=W0221
        if not os.path.isdir(catalog_root_dir):
            raise ValueError('Catalog directory {} does not exist'.format(catalog_root_dir))

        self.lightcone = kwargs.get('lightcone', True)

        get_file_list = self._get_healpix_file_list if self.lightcone else self._get_snapshot_file_list
        self._file_list = get_file_list(
            catalog_root_dir,
            catalog_filename_template,
            **kwargs
        )
        self._healpix_files = self._file_list # for backward compatibility

        self.cosmology = None
        if 'cosmology' in kwargs:
            self.cosmology = FlatLambdaCDM(**kwargs['cosmology'])

        self.version = kwargs.get('version', '0.0.0')
        if StrictVersion(__version__) < self.version:
            raise ValueError('Reader version {} is less than config version {} for'.format(__version__, self.version))

        self.file_check_info = dict()
        if kwargs.get('check_md5', True) or kwargs.get('check_size', True):
            try:
                with open(CHECK_FILE_PATH, 'r') as f:
                    self.file_check_info = yaml.safe_load(f)
            except (IOError, OSError):
                pass
            else:
                self.file_check_info = self.file_check_info.get(self.version, dict())
            if not self.file_check_info:
                warnings.warn('Cannot find valid infomation for file checks! Version {} not available in {}'.format(self.version, CHECK_FILE_PATH))

        # setting metadata (e.g., sky_area, box_size, redshift)
        meta_dict, self._native_quantities, self._quantity_info = self._process_metadata(**kwargs)
        for key, value in meta_dict.items():
            setattr(self, key, value)

        if self.lightcone:
            self._native_filter_quantities = {'healpix_pixel', 'redshift_block_lower'}
        else:
            self._native_filter_quantities = {'block'}

        self._quantity_modifiers = self._generate_quantity_modifiers()
        self.halo_mass_def = kwargs.get('halo_mass_def', 'FoF, b=0.168')

    def _get_group_names(self, fh): # pylint: disable=W0613
        return ['galaxyProperties']

    def _generate_native_quantity_list(self):
        return self._native_quantities

    @staticmethod
    def _generate_quantity_modifiers():
        return {}

    @staticmethod
    def _get_healpix_file_list(catalog_root_dir, catalog_filename_template, # pylint: disable=W0613
                               zlo=None, zhi=None, healpix_pixels=None,
                               check_file_list_complete=True, **kwargs):

        healpix_files = dict()
        fname_pattern = catalog_filename_template.format(r'(\d)', r'(\d)', r'(\d+)')
        for f in sorted(os.listdir(catalog_root_dir)):
            m = re.match(fname_pattern, f)
            if m is None:
                continue

            zlo_this, zhi_this, hpx_this = tuple(map(int, m.groups()))

            # check if this file is needed
            if ((zlo is not None and zhi_this <= zlo) or
                (zhi is not None and zlo_this >= zhi) or
                (healpix_pixels is not None and hpx_this not in healpix_pixels)):
                continue

            healpix_files[(zlo_this, hpx_this)] = os.path.join(catalog_root_dir, f)

        if check_file_list_complete:
            if zlo is None:
                zlo = min(z for z, _ in healpix_files)
            if zhi is None:
                zhi = max(z for z, _ in healpix_files) + 1
            possible_hpx = list(set(hpx for _, hpx in healpix_files)) if healpix_pixels is None else healpix_pixels
            if not all(key in healpix_files for key in product(range(zlo, zhi), possible_hpx)):
                raise ValueError('Some catalog files are missing!')

        return healpix_files

    @staticmethod
    def _get_snapshot_file_list(catalog_root_dir, catalog_filename_template, # pylint: disable=W0613
                                blocks=None, check_file_list_complete=True, **kwargs):

        snapshot_files = dict()

        fname_pattern = catalog_filename_template.format(r'(\d+)')

        for f in sorted(os.listdir(catalog_root_dir)):
            m = re.match(fname_pattern, f)
            if m is None:
                continue

            block_this = int(m.groups()[0])

            # check if this file is needed
            if (blocks is not None and block_this not in blocks):
                continue

            snapshot_files[block_this] = os.path.join(catalog_root_dir, f)

        if check_file_list_complete and blocks is not None:
            if not all(block_this in snapshot_files for block_this in blocks):
                raise ValueError('Some catalog files are missing!')

        return snapshot_files

    def _collect_native_quantities(self, fh, collect_info_dict=False):
        native_quantities = set()
        collect = partial(_add_to_native_quantity_collector, collector=native_quantities)
        group_name = first(self._get_group_names(fh))

        fh[group_name].visititems(collect)

        if collect_info_dict:
            quantity_info_dict = dict()
            modifier = lambda k, v: None if k == 'description' and decode(v) == 'None given' else decode(v)
            for quantity in native_quantities:
                quantity_info_dict[quantity] = {k: modifier(k, v) for k, v in fh[group_name][quantity].attrs.items()}
            return native_quantities, quantity_info_dict

        return native_quantities

    def _check_version(self, fh, file_name):
        catalog_version = list()
        for version_label in ('Major', 'Minor', 'MinorMinor'):
            try:
                catalog_version.append(fh['/metaData/version' + version_label][()])
            except KeyError:
                break
        catalog_version = StrictVersion('.'.join(map(str, catalog_version or (0, 0))))
        config_version = StrictVersion(self.version)
        if config_version != catalog_version:
            raise ValueError('Catalog version {} does not match config version {} for healpix file {}'.format(catalog_version, config_version, file_name))

    def _check_cosmology(self, fh, file_name, atol):
        for name_hdf5, name_astropy in (('H_0', 'h'), ('Omega_matter', 'Om0'), ('Omega_b', 'Ob0')):
            try:
                value_catalog = fh['metaData/{}'.format(name_hdf5)][()]
            except KeyError:
                warnings.warn('missing cosmology {} in metadata for healpix file {}'.format(name_hdf5, file_name))
                continue
            if name_hdf5 == 'H_0':
                value_catalog /= 100.0
            value_config = getattr(self.cosmology, name_astropy)
            if abs(value_catalog - value_config) > atol:
                raise ValueError('Mismatch in cosmological parameters ({} should be {}, not {}) for healpix file {}'.format(name_hdf5, value_config, value_catalog, file_name))

    def _process_metadata(self, ensure_quantity_consistent=False,
                          check_version=True, check_md5=True, check_size=True,
                          check_cosmology=True, cosmology_atol=1e-4,
                          sky_area=None, ensure_meta_consistent=True,
                          **kwargs):
        meta_dict = dict()
        native_quantities = None
        quantity_info = None

        calc_sky_area = bool(self.lightcone and not sky_area)

        if calc_sky_area:
            sky_area = dict()
            max_healpixel = max(hpx_this for _, hpx_this in self._healpix_files)
            min_valid_nside = hp.pixelfunc.get_min_valid_nside(max_healpixel)
            default_sky_area = hp.nside2pixarea(min_valid_nside, degrees=True)

        if check_size and 'size' not in self.file_check_info:
            check_size = False
            warnings.warn('Not able to perform size check: no size specified in {}'.format(CHECK_FILE_PATH))

        if check_md5 and 'md5' not in self.file_check_info:
            check_md5 = False
            warnings.warn('Not able to perform md5 check: no md5 sum specified in {}'.format(CHECK_FILE_PATH))

        for file_key, file_path in self._file_list.items():
            file_name = os.path.basename(file_path)

            if check_size and os.path.getsize(file_path) != self.file_check_info['size'].get(file_name):
                raise ValueError('File size does not match for healpix file {}'.format(file_name))

            if check_md5 and md5(file_path) != self.file_check_info['md5'].get(file_name):
                raise ValueError('md5 sum does not match for healpix file {}'.format(file_name))

            with h5py.File(file_path, 'r') as fh:
                if check_version:
                    self._check_version(fh, file_name)

                if check_cosmology:
                    self._check_cosmology(fh, file_name, cosmology_atol)

                if calc_sky_area:  # get sky area
                    try:
                        sky_area_this = fh['metaData/skyArea'][()]
                    except KeyError:
                        sky_area_this = default_sky_area
                    sky_area_this = float(sky_area_this)
                    hpx_this = file_key[1]
                    if sky_area.get(hpx_this, 0) < sky_area_this:
                        sky_area[hpx_this] = sky_area_this

                elif not self.lightcone:  # get meta info for boxes (box size and redshift)
                    for key in ('box_size', 'redshift'):
                        try:
                            value_this = fh['metaData/' + key][()]
                        except KeyError:
                            pass
                        else:
                            value_this = float(value_this)
                            if key not in meta_dict:
                                meta_dict[key] = value_this
                            elif meta_dict[key] != value_this:
                                warnings.warn('found inconsistency in {}'.format(key))

                # get native quantities
                if native_quantities is None or quantity_info is None:
                    native_quantities, quantity_info = self._collect_native_quantities(fh, collect_info_dict=True)
                elif (ensure_quantity_consistent and
                      native_quantities != self._collect_native_quantities(fh)):
                    raise ValueError('native quantities are not consistent among different files')

            # Break the loop if no more check needed
            if not (calc_sky_area or check_size or check_md5 or ensure_quantity_consistent or ensure_meta_consistent):
                break

        if self.lightcone:
            if isinstance(sky_area, dict):
                sky_area = sum(sky_area.values())
            else:
                sky_area = float(sky_area)
            meta_dict['sky_area'] = sky_area

        else:
            if 'redshift' not in meta_dict:
                filename = os.path.basename(first(self._file_list.values()))
                m = re.search(r'z(\d+(?:\.\d+)?)', filename)
                meta_dict['redshift'] = float(m.groups()[0]) if m else None

            if 'box_size' not in meta_dict:
                meta_dict['box_size'] = getattr(self, '_default_box_size', None)

        return meta_dict, native_quantities, quantity_info

    def _iter_native_dataset(self, native_filters=None):
        if self.lightcone:
            key_to_dict = lambda key: dict(zip(('redshift_block_lower', 'healpix_pixel'), key))
        else:
            key_to_dict = lambda key: {'block': key}
        for key, file_path in self._file_list.items():
            d = key_to_dict(key)
            if native_filters is not None and not native_filters.check_scalar(d):
                continue
            with h5py.File(file_path, 'r') as fh:
                for group in self._get_group_names(fh):
                    # pylint: disable=W0640
                    if len(fh[group]):
                        yield lambda native_quantity: fh['{}/{}'.format(group, native_quantity)][()]

    def _get_quantity_info_dict(self, quantity, default=None):
        q_mod = self.get_quantity_modifier(quantity)
        if callable(q_mod) or (isinstance(q_mod, (tuple, list)) and len(q_mod) > 1 and callable(q_mod[0])):
            warnings.warn('This value is composed of a function on native quantities. So we have no idea what the units are')
            return default
        return self._quantity_info.get(q_mod or quantity, default)

    @property
    def available_healpix_pixels(self):
        if not self.lightcone:
            raise AttributeError("Non-lightcone catalog has no attribute 'available_healpix_pixels'")
        return sorted(set(k[1] for k in self._file_list))


class CosmoDC2GalaxyCatalog(CosmoDC2ParentClass):
    """
    CosmoDC2 galaxy catalog reader, inherited from CosmoDC2ParentClass
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
            'convergence': 'convergence',
            'magnification': (lambda mag: np.where(mag < 0.2, 1.0, mag), 'magnification'),
            'halo_id':       'uniqueHaloID',
            'halo_mass':     (lambda x: x/self.cosmology.h, 'hostHaloMass'),
            'is_central':    (lambda x: x.astype(bool), 'isCentral'),
            'stellar_mass':  'totalMassStellar',
            'stellar_mass_disk':        'diskMassStellar',
            'stellar_mass_bulge':       'spheroidMassStellar',
            'size_disk_true':           'morphology/diskHalfLightRadiusArcsec',
            'size_bulge_true':          'morphology/spheroidHalfLightRadiusArcsec',
            'size_minor_disk_true':     'morphology/diskMinorAxisArcsec',
            'size_minor_bulge_true':    'morphology/spheroidMinorAxisArcsec',
            'position_angle_true_dc2':  (_gen_position_angle, 'morphology/positionAngle'),
            'position_angle_true_phosim': 'morphology/positionAngle',
            'position_angle_true':      (np.negative, 'morphology/positionAngle'),
            'sersic_disk':              'morphology/diskSersicIndex',
            'sersic_bulge':             'morphology/spheroidSersicIndex',
            'ellipticity_true':         'morphology/totalEllipticity',
            'ellipticity_disk_true':         'morphology/diskEllipticity',
            'ellipticity_bulge_true':        'morphology/spheroidEllipticity',
            'ellipticity_1_true_dc2':       (_calc_ellipticity_1_dc2, 'morphology/totalEllipticity'),
            'ellipticity_2_true_dc2':       (_calc_ellipticity_2_dc2, 'morphology/totalEllipticity'),
            'ellipticity_1_disk_true_dc2':  (_calc_ellipticity_1_dc2, 'morphology/diskEllipticity'),
            'ellipticity_2_disk_true_dc2':  (_calc_ellipticity_2_dc2, 'morphology/diskEllipticity'),
            'ellipticity_1_bulge_true_dc2': (_calc_ellipticity_1_dc2, 'morphology/spheroidEllipticity'),
            'ellipticity_2_bulge_true_dc2': (_calc_ellipticity_2_dc2, 'morphology/spheroidEllipticity'),
            'ellipticity_1_true':       (_calc_ellipticity_1, 'morphology/totalEllipticity', 'morphology/positionAngle'),
            'ellipticity_2_true':       (_calc_ellipticity_2, 'morphology/totalEllipticity', 'morphology/positionAngle'),
            'ellipticity_1_disk_true':  (_calc_ellipticity_1, 'morphology/diskEllipticity', 'morphology/positionAngle'),
            'ellipticity_2_disk_true':  (_calc_ellipticity_2, 'morphology/diskEllipticity', 'morphology/positionAngle'),
            'ellipticity_1_bulge_true': (_calc_ellipticity_1, 'morphology/spheroidEllipticity', 'morphology/positionAngle'),
            'ellipticity_2_bulge_true': (_calc_ellipticity_2, 'morphology/spheroidEllipticity', 'morphology/positionAngle'),
            'size_true': (
                _calc_weighted_size,
                'morphology/diskHalfLightRadiusArcsec',
                'morphology/spheroidHalfLightRadiusArcsec',
                'LSST_filters/diskLuminositiesStellar:LSST_r:rest',
                'LSST_filters/spheroidLuminositiesStellar:LSST_r:rest',
            ),
            'size_minor_true': (
                _calc_weighted_size_minor,
                'morphology/diskHalfLightRadiusArcsec',
                'morphology/spheroidHalfLightRadiusArcsec',
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
                quantity_modifiers['mag_{}_sdss'.format(band)] = (_calc_lensed_magnitude, 'SDSS_filters/magnitude:SDSS_{}:observed:dustAtlas'.format(band), 'magnification',)
                quantity_modifiers['mag_{}_sdss_no_host_extinction'.format(band)] = (_calc_lensed_magnitude, 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band), 'magnification',)
                quantity_modifiers['mag_true_{}_sdss'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed:dustAtlas'.format(band)
                quantity_modifiers['mag_true_{}_sdss_no_host_extinction'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band)
                quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest:dustAtlas'.format(band)
                quantity_modifiers['Mag_true_{}_sdss_z0_no_host_extinction'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest'.format(band)

            quantity_modifiers['mag_{}_lsst'.format(band)] = (_calc_lensed_magnitude, 'LSST_filters/magnitude:LSST_{}:observed:dustAtlas'.format(band.lower()), 'magnification',)
            quantity_modifiers['mag_{}_lsst_no_host_extinction'.format(band)] = (_calc_lensed_magnitude, 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower()), 'magnification',)
            quantity_modifiers['mag_true_{}_lsst'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed:dustAtlas'.format(band.lower())
            quantity_modifiers['mag_true_{}_lsst_no_host_extinction'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower())
            quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest:dustAtlas'.format(band.lower())
            quantity_modifiers['Mag_true_{}_lsst_z0_no_host_extinction'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest'.format(band.lower())

            if band != 'Y':
                quantity_modifiers['mag_{}'.format(band)] = quantity_modifiers['mag_{}_lsst'.format(band)]
                quantity_modifiers['mag_true_{}'.format(band)] = quantity_modifiers['mag_true_{}_lsst'.format(band)]

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

        # make quantity modifiers work in older versions
        version = StrictVersion(self.version)
        if version < StrictVersion('0.4.6'):
            quantity_modifiers['halo_id'] = 'UMachineNative/halo_id'

        if version < StrictVersion('0.4.4'):
            self._native_quantities.difference_update(set(q for q in self._native_quantities if (
                q.startswith('emissionLines/') or q.endswith('ContinuumLuminosity')
            )))

        if version <= StrictVersion('0.2'):
            quantity_modifiers['halo_id'] = 'hostHaloTag'

        return quantity_modifiers


    def _collect_native_quantities(self, fh, collect_info_dict=False):
        orig_output = super()._collect_native_quantities(fh, collect_info_dict)
        # a hot fix of the unit of native halo mass (hostHaloMass), which should be Msun/h
        if collect_info_dict:
            orig_output[1]['hostHaloMass']['units'] = 'Msun/h'
        return orig_output


class SkySim5000GalaxyCatalog(CosmoDC2GalaxyCatalog):
    """
    SkySim5000  galaxy catalog reader, inherited from CosmoDC2GalaxyCatalog
    """

    def _generate_quantity_modifiers(self):
        quantity_modifiers = super()._generate_quantity_modifiers()

        #change magnification definition
        quantity_modifiers['magnification'] = (_limit_magnification, 'magnification')

        #change magnitude computation
        for band in 'ugrizyY':
            if band != 'y' and band != 'Y':
                quantity_modifiers['mag_{}_sdss'.format(band)] = (_calc_lensed_magnitude_with_limits, 'SDSS_filters/magnitude:SDSS_{}:observed:dustAtlas'.format(band), 'magnification',)
                quantity_modifiers['mag_{}_sdss_no_host_extinction'.format(band)] = (_calc_lensed_magnitude_with_limits, 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band), 'magnification',)
        quantity_modifiers['mag_{}_lsst'.format(band)] = (_calc_lensed_magnitude_with_limits, 'LSST_filters/magnitude:LSST_{}:observed:dustAtlas'.format(band.lower()), 'magnification',)
        quantity_modifiers['mag_{}_lsst_no_host_extinction'.format(band)] = (_calc_lensed_magnitude_with_limits, 'LSST_filters/magnitude:LSST_{}:observed'.format(band.lower()), 'magnification',)

        return quantity_modifiers


class DiffSkyGalaxyCatalog(CosmoDC2ParentClass):
    """
    DiffSky galaxy catalog reader, inherited from CosmoDC2ParentClass
    Class for new generation of catalogs generated with JAX-based
    forward modeling techniques.
    This reader is used by the skysim_v3, diffsky and roman_rubin_2023 catalog series
    """

    def _get_group_names(self, fh):
        return [k for k in fh if k.isdigit()]

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'galaxy_id' :    'galaxy_id',
            'ra_true':       'ra',
            'dec_true':      'dec',
            'redshift':      'redshift',
            'redshift_true': 'redshiftHubble',
            'shear_1':       'shear1',
            'shear_2':       'shear2',
            'shear_2_phosim': (np.negative, 'shear2'),
            'shear_2_treecorr':   'shear2',
            'convergence': 'convergence',
            'magnification': (lambda mag: np.where(mag < 0.2, 1.0, mag), 'magnification'),
            'halo_id':       'target_halo_id',
            'halo_mass':     (lambda x: x/self.cosmology.h, 'target_halo_mass'),
            'stellar_mass':  (lambda x: np.power(10, x), 'logsm_obs'),
            'bulge_to_total_ratio':     'bulge_frac',
            'size_disk_true':           'diskHalfLightRadiusArcsec',
            'size_bulge_true':          'spheroidHalfLightRadiusArcsec',
            'position_angle_true_phosim': 'positionAngle',
            'position_angle_true':      (np.negative, 'positionAngle'),
            'ellipticity_true':         'totalEllipticity',
            'ellipticity_disk_true':    'diskEllipticity',
            'ellipticity_bulge_true':   'spheroidEllipticity',
            'position_x': (lambda x: x/self.cosmology.h, 'x'),
            'position_y': (lambda x: x/self.cosmology.h, 'y'),
            'position_z': (lambda x: x/self.cosmology.h, 'z'),
            'velocity_x': 'vx',
            'velocity_y': 'vy',
            'velocity_z': 'vz',
        }

        #check for quantity options to ensure backwards compatibility
        hsc_list = [q for q in self._native_quantities if 'hsc' in q]
        if 'um_source_galaxy_upid' in self._native_quantities:
            quantity_modifiers['is_central'] = (lambda x: x == -1, 'um_source_galaxy_upid')
        else:
            quantity_modifiers['is_central'] = (lambda x: x == -1, 'source_galaxy_upid')

        # add magnitudes
        for band in 'ugrizyY':
            if band != 'y' and band != 'Y':
                quantity_modifiers['mag_{}_sdss'.format(band)] = (_calc_lensed_magnitude, 'SDSS_obs_{}'.format(band),
                                                                  'magnification',)
                quantity_modifiers['mag_true_{}_sdss'.format(band)] = 'SDSS_obs_{}'.format(band.lower())
                quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'SDSS_rest_{}'.format(band.upper())

            if band != 'u' and band != 'Y' and hsc_list:
                quantity_modifiers['mag_{}_hsc'.format(band)] = (_calc_lensed_magnitude, 'HSC_obs_{}'.format(band),
                'magnification',)
                quantity_modifiers['mag_true_{}_hsc'.format(band)] = 'HSC_obs_{}'.format(band.lower())
                quantity_modifiers['Mag_true_{}_hsc_z0'.format(band)] = 'HSC_rest_{}'.format(band.upper())

            quantity_modifiers['mag_{}_lsst'.format(band)] = (_calc_lensed_magnitude, 'LSST_obs_{}'.format(band.lower(
            )), 'magnification',)
            quantity_modifiers['mag_true_{}_lsst'.format(band)] = 'LSST_obs_{}'.format(band.lower())
            quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'LSST_rest_{}'.format(band.upper())

            if band != 'Y':
                quantity_modifiers['mag_{}'.format(band)] = quantity_modifiers['mag_{}_lsst'.format(band)]
                quantity_modifiers['mag_true_{}'.format(band)] = quantity_modifiers['mag_true_{}_lsst'.format(band)]

        return quantity_modifiers


class BaseDC2GalaxyCatalog(CosmoDC2ParentClass):
    """
    BaseDC2 galaxy catalog reader, inherited from CosmoDC2ParentClass
    """
    def _get_group_names(self, fh):
        return [k for k in fh if k.isdigit()]

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'galaxy_id' :    'galaxy_id',
            'ra_true':       'ra',
            'dec_true':      'dec',
            'redshift_true': 'redshift',
            'halo_id':       'target_halo_id',
            'halo_mass':     (lambda x: x/self.cosmology.h, 'target_halo_mass'),
            'stellar_mass':  'obs_sm',
            'position_x': (lambda x: x/self.cosmology.h, 'x'),
            'position_y': (lambda x: x/self.cosmology.h, 'y'),
            'position_z': (lambda x: x/self.cosmology.h, 'z'),
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


class BaseDC2SnapshotGalaxyCatalog(CosmoDC2ParentClass):
    """
    BaseDC2 snapshot galaxy catalog reader, inherited from CosmoDC2ParentClass
    """
    _default_box_size = 3000.0

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'galaxy_id' :    'galaxy_id',
            'halo_id':       'target_halo_id',
            'halo_mass':     (lambda x: x/self.cosmology.h, 'target_halo_mass'),
            'stellar_mass':  'obs_sm',
            'position_x': (lambda x: x/self.cosmology.h, 'x'),
            'position_y': (lambda x: x/self.cosmology.h, 'y'),
            'position_z': (lambda x: x/self.cosmology.h, 'z'),
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


class BaseDC2ShearCatalog(BaseDC2GalaxyCatalog):
    """
    BaseDC2 shear catalog reader, inherited from BaseDC2GalaxyCatalog
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


class CosmoDC2AddonCatalog(CosmoDC2ParentClass):
    def _get_group_names(self, fh): # pylint: disable=W0613
        return [self.get_catalog_info('addon_group')]
