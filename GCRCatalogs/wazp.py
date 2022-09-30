"""
WaZP catalog class.
"""
import os
import yaml
from .redmapper import RedmapperCatalog

__all__ = ['WazpCatalog',]

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_wazp_v1.0_meta.yaml')

class WazpCatalog(RedmapperCatalog):
    """
    WaZP cluster catalog class.  Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class with functionalities from
    RedmapperCatalog.
    """
    def _subclass_init(self, *args, **kwargs):
        RedmapperCatalog._subclass_init(self, *args, **kwargs)
        self._quantity_info_dict = self._generate_info_dict(META_PATH)

    def _generate_info_dict(self, meta_path):
        """Creates a 2d dictionary with information for each homogenized quantity

        Args:
            meta_path (path): Path of yaml config file with object meta data
            bands (list or None): A list of band names.

        Returns:
            Dictionary of the form
                {<homonogized value (str)>: {<meta value (str)>: <meta data>}, ...}
        """
        out = {}
        with open(meta_path, 'r') as f:
            base_dict = yaml.safe_load(f)
        for key, value in self._quantity_modifiers.items():
            out[key] = base_dict[value]
        out.update(base_dict)
        return out

    def _get_quantity_info_dict(self, quantity, default=None):
        return self._quantity_info_dict.get(quantity, default)

    def print_quantity_info(self, quantity):
        """
        Print information of a certain quantity.
        """
        if quantity in  self._quantity_info_dict:
            info = self._quantity_info_dict.get(quantity)
            unit = f', unit:{info["unit"]}' if info['unit']!='none' else ''
            return f'({info["type"]}{unit}): {info["description"]}'
        else:
            return None

    def _generate_quantity_modifiers(self):
        return {
            'cluster_id': 'clusters/ID',
            'cluster_ra': 'clusters/RA',
            'cluster_dec': 'clusters/DEC',
            'cluster_z': 'clusters/zp_bright',
            'cluster_ngals': 'clusters/NGALS',
            'cluster_radius_mpc': 'clusters/RADIUS_MPC',
            'cluster_radius_arcmin': 'clusters/RADIUS_AMIN',
            'cluster_snr': 'clusters/SNR',
            'cluster_nmem': 'clusters/NMEM',
            'cluster_masked_frac_1mpc': 'clusters/MASKED_FRAC_1MPC',
            'cluster_mstar_cl': 'clusters/MSTAR_CL',
            'cluster_dist_bcg': 'clusters/DIST_BCG',
            'cluster_ra_bcg': 'clusters/RA_BCG',
            'cluster_dec_bcg': 'clusters/DEC_BCG',
            'cluster_zp_bcg': 'clusters/ZP_BCG',
            'member_id': 'members/ID_g',
            'member_id_cluster': 'members/ID_CLUSTER',
            'member_ra': 'members/RA',
            'member_dec': 'members/DEC',
            'member_z': 'members/ZP',
            'member_pmem': 'members/PMEM',
            'member_pmem_err': 'members/PMEM_ERR',
            'member_mstar_cl': 'members/MSTAR_CL',
            'member_flag_bcg': 'members/FLAG_BCG',
            'member_flag_bcg_cen': 'members/FLAG_BCG_CEN',
            'member_dcen': 'members/DCEN',
            'member_dcen_norm': 'members/DCEN_NORM',
            'member_snr': 'members/SNR',
            'member_mag_g': 'members/mag_g',
            'member_mag_r': 'members/mag_r',
            'member_mag_i': 'members/mag_i',
            'member_mag_z': 'members/mag_z',
            'member_mag_y': 'members/mag_y',
            }
