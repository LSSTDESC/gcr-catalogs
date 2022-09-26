"""
WaZP catalog class.
"""
from .redmapper import RedmapperCatalog

__all__ = ['WazpCatalog',]


class WazpCatalog(RedmapperCatalog):
    """
    WaZP cluster catalog class.  Uses generic quantity and filter mechanisms
    defined by BaseGenericCatalog class with functionalities from
    RedmapperCatalog.
    """

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

########################
### ALL WaZP columns ###
########################
# ID
# SeqNr
# DETECTION_TILE
# IZ_INIT
# IZ_FINAL
# PEAK_ID_TILE_IZ
# ID_IN_TILE
# RA
# DEC
# zp
# zp_median
# Z_INIT
# ZMIN_CL
# ZMAX_CL
# ZMIN_95_CL
# ZMAX_95_CL
# MSTAR_CL
# XPEAK
# YPEAK
# RADIUS_ISO_MPC
# RADIUS_SADDLE_MPC
# MAXWAVE
# FLUX_WAVE
# FLAG_MERGE
# SIGMA_DZ_INIT
# SIGMA_DZ_EFF
# FLAG_ZP
# NGAL_FOR_ZP
# FLAG_IZ
# GLOBAL_NBKG_ZM
# GLOBAL_LBKG_ZM
# SIG_NBKG_ZM
# SIG_LBKG_ZM
# LOCAL_NBKG_ZM
# LOCAL_LBKG_ZM
# AREA_LOCAL_BKG
# MASKED_FRAC_1MPC
# MASKED_FRAC_05MPC
# MASKED_FRAC_03MPC
# SNR
# SNR_NGALS
# SNR_LGALS
# CONTRAST_NGALS
# CONTRAST_LGALS
# DMAG_CORE
# DMAG_BCG
# DIST_BCG
# NGALS_TEST
# NGALS_CEN
# LGALS_CEN
# LOCAL_NBKG
# LOCAL_LBKG
# GLOBAL_NBKG
# GLOBAL_LBKG
# SIG_NBKG
# SIG_LBKG
# OUT_OF_CYL
# CYL_NSL
# PARENT_CYL_NSL
# ZMIN_CYL
# ZMAX_CYL
# IZ_MIN_CYL
# IZ_MAX_CYL
# CONTRAST_CYL
# NMAX_CYL
# KING_Rc
# KING_D0
# KING_CHI2
# KING_NFIT
# RADIUS_MPC
# RADIUS_AMIN
# RADIUS_MAX_CONTRAST
# RADIUS_SCALING
# NGALS_MODEL_FIT
# NGALS_MODEL
# FLAG_DUPLICATE
# RADIUS_500kpc_amin
# RADIUS_1Mpc_amin
# NMEM
# NGALS
# NGALS_R300
# NGALS_R500
# LGALS
# LGALS_R300
# LGALS_R500
# E_NGALS
# E_NGALS_R300
# E_NGALS_R500
# E_LGALS
# E_LGALS_R300
# E_LGALS_R500
# RA_BCG
# DEC_BCG
# ZP_BCG
# zp_bright
# zs
# zs_min
# zs_max
# zp_err
# rank

################################
### ALL WaZP members columns ###
################################
# SeqNr
# ID_CLUSTER_TILE
# DETECTION_TILE
# ID_g
# NMEM_CL
# PMEM
# PMEM_ERR
# MAG
# RA
# DEC
# RA_CL
# DEC_CL
# ZP
# ZP_CL
# MSTAR_CL
# mag_bcg
# FLAG_BCG
# mag_bcg_cen
# FLAG_BCG_CEN
# DCEN
# DCEN_NORM
# SNR
# NGALS
# mag_u
# mag_g
# mag_r
# mag_i
# mag_z
# mag_y
# mag_j
# mag_h
# mag_k
# zs
# zs_flag
# ID_CLUSTER
