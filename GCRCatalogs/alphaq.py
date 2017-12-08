"""
Alpha Q galaxy catalog class.
"""
from __future__ import division
import os
import numpy as np
import h5py
import warnings
from .cosmology import Cosmology
from GCR import BaseGenericCatalog
from distutils.version import StrictVersion
__all__ = ['AlphaQGalaxyCatalog']


class AlphaQGalaxyCatalog(BaseGenericCatalog):
    """
    Alpha Q galaxy catalog class. Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, filename, **kwargs):

        assert os.path.isfile(filename), 'Catalog file {} does not exist'.format(filename)
        self._file = filename
        self.lightcone = kwargs.get('lightcone')

        with h5py.File(self._file, 'r') as fh:
            H0 = fh['metaData/simulationParameters/H_0'].value,
            Omega_m = fh['metaData/simulationParameters/Omega_matter'].value
            Omega_b = fh['metaData/simulationParameters/Omega_b'].value

            catalog_version = list()
            for version_label in ('Major', 'Minor', 'MinorMinor'):
                try:
                    catalog_version.append(fh['/metaData/version' + version_label].value)
                except KeyError:
                    break

        self.cosmology = Cosmology(Omega_c=Omega_m-Omega_b, Omega_b=Omega_b, h=H0/100.0)

        catalog_version = StrictVersion('.'.join(map(str, catalog_version or (2, 0))))
        config_version = StrictVersion(kwargs.get('version', '0.0'))
        if config_version != catalog_version:
            raise ValueError('Catalog file version {} does not match config version {}'.format(catalog_version, config_version))


        self._quantity_modifiers = {
            'galaxy_id' :         'galaxyID',
            'ra':                 'ra',
            'dec':                'dec',
            'ra_true':            'ra_true',
            'dec_true':           'dec_true',
            'redshift':           'redshift',
            'redshift_true':      'redshiftHubble',
            'shear_1':            'shear1',
            'shear_2':            'shear2',
            'convergence':        'convergence',
            'magnification':      'magnification',
            'halo_id':            'hostIndex',
            'halo_mass':          'hostHaloMass',
            'is_central':         (lambda x : x.astype(np.bool), 'isCentral'),
            'stellar_mass':       'totalMassStellar',
            'size_disk_true':     'morphology/diskHalfLightRadius',
            'size_bulge_true':    'morphology/spheroidHalfLightRadius',
            'disk_sersic_index':  'morphology/diskSersicIndex',
            'bulge_sersic_index': 'morphology/spheroidSersicIndex',
            'ellipticity_1':      'morphology/totalEllipticity1',
            'ellipticity_2':      'morphology/totalEllipticity2',
            'position_x':         'x',
            'position_y':         'y',
            'position_z':         'z',
            'velocity_x':         'vx',
            'velocity_y':         'vy',
            'velocity_z':         'vz',
        }

        # to be backward compatible
        if catalog_version < StrictVersion('2.1.1'):
            self._quantity_modifiers.update({
                'disk_sersic_index':  'diskSersicIndex',
                'bulge_sersic_index': 'spheroidSersicIndex',
            })
            del self._quantity_modifiers['ellipticity_1']
            del self._quantity_modifiers['ellipticity_2']

        if catalog_version == StrictVersion('2.0'):
            self._quantity_modifiers.update({
                'ra':       (lambda x: x/3600, 'ra'),
                'ra_true':  (lambda x: x/3600, 'ra_true'),
                'dec':      (lambda x: x/3600, 'dec'),
                'dec_true': (lambda x: x/3600, 'dec_true'),
            })

        if catalog_version < StrictVersion('2.0'):
            raise ValueError('That is not possible!')

        for band in 'ugriz':
            self._quantity_modifiers['mag_{}_lsst'.format(band)] = 'LSST_filters/magnitude:LSST_{}:observed'.format(band)
            self._quantity_modifiers['mag_{}_sdss'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:observed'.format(band)
            self._quantity_modifiers['Mag_true_{}_lsst_z0'.format(band)] = 'LSST_filters/magnitude:LSST_{}:rest'.format(band)
            self._quantity_modifiers['Mag_true_{}_sdss_z0'.format(band)] = 'SDSS_filters/magnitude:SDSS_{}:rest'.format(band)

        self._quantity_modifiers['mag_Y_lsst'] = 'LSST_filters/magnitude:LSST_y:observed'
        self._quantity_modifiers['Mag_true_Y_lsst_z0'] = 'LSST_filters/magnitude:LSST_y:rest'


    def _generate_native_quantity_list(self):
        with h5py.File(self._file, 'r') as fh:
            hgroup = fh['galaxyProperties']
            hobjects = []
            #get all the names of objects in this tree
            hgroup.visit(hobjects.append)
            #filter out the group objects and keep the dataste objects
            hdatasets = [hobject for hobject in hobjects if type(hgroup[hobject]) == h5py.Dataset]
            native_quantities = set(hdatasets)
        return native_quantities


    def _iter_native_dataset(self, native_filters=None):
        assert not native_filters, '*native_filters* is not supported'
        with h5py.File(self._file, 'r') as fh:
            def native_quantity_getter(native_quantity):
                return fh['galaxyProperties/{}'.format(native_quantity)].value
            yield native_quantity_getter


    def _get_native_quantity_info_dict(self, quantity, default=None):
        with h5py.File(self._file, 'r') as fh:
            quantity_key = 'galaxyProperties/' + quantity
            if quantity_key not in fh:
                return default
            modifier = lambda k, v: None if k=='description' and v==b'None given' else v.decode()
            return {k: modifier(k, v) for k, v in fh[quantity_key].attrs.items()}


    def _get_quantity_info_dict(self, quantity, default=None):
        q_mod = self.get_quantity_modifier(quantity)
        if callable(q_mod) or (isinstance(q_mod, (tuple, list)) and len(q_mod) > 1 and callable(q_mod[0])):
            warnings.warn('This value is composed of a function on native quantities. So we have no idea what the units are')
            return default
        return self._get_native_quantity_info_dict(q_mod or quantity, default=default)
