"""
redMaPPer catalog class.
"""
from __future__ import division, print_function
import os
import functools
from astropy.io import fits
from GCR import BaseGenericCatalog
from .cosmology import FlatLambdaCDM

__all__ = ['RedmapperCatalog', 'RedMapperLegacyCatalog']


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


class RedmapperCatalog(BaseGenericCatalog):
    """
    redMaPPer cluster catalog class.  Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class.
    """

    def _subclass_init(self, catalog_root_dir,
                       catalog_path_template,
                       use_cache=True,
                       **kwargs): #pylint: disable=W0221

        if not os.path.isdir(catalog_root_dir):
            raise RuntimeError("Catalog directory %s does not exist." % (catalog_root_dir))

        self._catalog_path_template = {k: os.path.join(catalog_root_dir, v) for k, v in catalog_path_template.items()}

        self.cosmology = None
        if 'cosmology' in kwargs:
            self.cosmology = FlatLambdaCDM(**kwargs['cosmology'])

        self.lightcone = kwargs.get('lightcone')
        self.sky_area = kwargs.get('sky_area')
        self.cache = dict() if use_cache else None
        self._members_only = kwargs.get('members_only')
        self._quantity_modifiers = self._generate_quantity_modifiers()

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'cluster_id_member': 'members/mem_match_id',
            'id_member': 'members/id',
            'ra_member': 'members/ra',
            'dec_member': 'members/dec',
            'refmag_member': 'members/refmag',
            'refmag_err_member': 'members/refmag_err',
            'redshift_true_member': 'members/zspec',
            'p_member': 'members/p',
            'pfree_member': 'members/pfree',
            'theta_i_member': 'members/theta_i',
            'theta_r_member': 'members/theta_r',
        }

        # Add magnitudes
        for i, band in enumerate(['g', 'r', 'i', 'z', 'y']):
            quantity_modifiers['mag_%s_lsst_member' % (band)] = 'members/mag/%d' % (i)
            quantity_modifiers['magerr_%s_lsst_member' % (band)] = 'members/mag_err/%d' % (i)

        if not self._members_only:
            quantity_modifiers.update({
                'cluster_id': 'clusters/mem_match_id',
                'ra': 'clusters/ra',
                'dec': 'clusters/dec',
                'redshift': 'clusters/z_lambda',
                'redshift_err': 'clusters/z_lambda_e',
                'richness': 'clusters/lambda',
                'richness_err': 'clusters/lambda_e',
                'scaleval': 'clusters/scaleval',
                'redshift_true_cg': 'clusters/cg_spec_z',
                'maskfrac': 'clusters/maskfrac',
            })

            # add centrals
            for i in range(5):
                quantity_modifiers['ra_cen_%d' % (i)] = 'clusters/ra_cent/%d' % (i)
                quantity_modifiers['dec_cen_%d' % (i)] = 'clusters/dec_cent/%d' % (i)
                quantity_modifiers['p_cen_%d' % (i)] = 'clusters/p_cen/%d' % (i)
                quantity_modifiers['id_cen_%d' % (i)] = 'clusters/id_cent/%d' % (i)

        return quantity_modifiers

    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise RuntimeError("*native_filters* not supported")

        yield functools.partial(self._native_quantity_getter)

    def _generate_native_quantity_list(self):
        native_quantities = set()

        for subset in self._catalog_path_template.keys():
            if self._members_only and subset == 'clusters':
                continue
            f = self._open_dataset(subset)
            for name, (dt, _) in f.data.dtype.fields.items():
                if dt.shape:
                    for i in range(dt.shape[0]):
                        native_quantities.add('/'.join((subset, name, str(i))))
                else:
                    native_quantities.add('/'.join((subset, name)))
        return native_quantities

    def _open_dataset(self, subset):
        path = self._catalog_path_template[subset]

        if self.cache is None:
            return FitsFile(path)

        if subset not in self.cache:
            self.cache[subset] = FitsFile(path)
        return self.cache[subset]

    def _native_quantity_getter(self, native_quantity):
        native_quantity = native_quantity.split('/')
        if len(native_quantity) not in (2, 3):
            raise RuntimeError('something wrong with the native_quantity {}'.format(native_quantity))
        subset = native_quantity.pop(0)
        column = native_quantity.pop(0)
        data = self._open_dataset(subset).data[column]
        if native_quantity:
            data = data[:,int(native_quantity.pop(0))]
        return data.byteswap().newbyteorder()


class RedMapperLegacyCatalog(RedmapperCatalog):
    """
    Legacy redMaPPer cluster catalog class.
    """

    def _generate_quantity_modifiers(self):
        quantity_modifiers = {
            'galaxy_id'         :   'members/ID',
            'cluster_id_member' :   'members/MEM_MATCH_ID',
            'ra'                :   'members/RA',
            'dec'               :   'members/DEC',
            'redshift_true'     :   'members/Z',
            'redshift'          :   'members/ZRED',
            'p_mem'             :   'members/P',
            'p_free'            :   'members/PFREE',
        }

        # add magnitudes
        for i, band in enumerate(['u','g','r','i','z']):
            quantity_modifiers['mag_{}_lsst'.format(band)] = 'members/MODEL_MAG/{}'.format(i)
            quantity_modifiers['magerr_{}_lsst'.format(band)] = 'members/MODEL_MAGERR/{}'.format(i)

        if not self._members_only:
            quantity_modifiers.update({
                'cluster_id'        :   'clusters/MEM_MATCH_ID',
                'ra_cluster'        :   'clusters/RA',
                'dec_cluster'       :   'clusters/DEC',
                'redshift_cluster'  :   'clusters/Z_LAMBDA',
                'redshift_true_cluster':'clusters/Z',
                'p_cen'             :   'clusters/P_BCG',
                'richness'          :   'clusters/LAMBDA_CHISQ',
                'halo_id'           :   'clusters/MEM_MATCH_ID',
                'halo_mass'         :   'clusters/M200',
                'lim_limmag_dered'  :   'clusters/LIM_LIMMAG_DERED',
                'scaleval'          :   'clusters/SCALEVAL',
            })

        return quantity_modifiers
