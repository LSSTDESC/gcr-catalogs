import numpy as np
import os

from scipy.spatial import KDTree

from lsst.utils import getPackageDir


__all__ = ["sed_from_galacticus_mags"]


def sed_from_galacticus_mags(galacticus_mags):
    """
    galacticus_mags is a numpy array such that
    galacticus_mags[i][j] is the magnitude of the jth star in the ith bandpass,
    where the bandpasses are ordered in ascending order of minimum wavelength.

    Will return a numpy array of SED names and a numpy array of magNorms.
    """

    if not hasattr(sed_from_galacticus_mags, '_sed_color_tree'):
        catsim_dir = os.path.join(getPackageDir('gcr_catalogs'),
                                  'CatSimSupport')
        color_grid_file = os.path.join(catsim_dir, 'CatSimColorGrid.txt')

        if not os.path.exists(color_grid_file):
            msg = '\n%s does not exist\n' % color_grid_file
            msg += 'Go into the directory %s ' % catsim_dir
            msg += 'and run the script get_sed_colors.py'
            raise RuntimeError(msg)

        dtype_list = [('name', str, 200)]
        for ii in range(30):
            dtype_list.append(('mag%d' % ii, float))
        dtype_list.append(('magNorm', float))
        dtype = np.dtype(dtype_list)
        sed_data = np.genfromtxt(color_grid_file, dtype=dtype)
        sed_colors = np.array([sed_data['mag%d' % ii+1] - sed_data['mag%d' % ii]
                               for ii in range(29)])
        sed_from_galacticus_mags._color_tree = KDTree(sed_colors.transpose(), leafsize=1)
        sed_from_galacticus_mags._sed_names = sed_data['name']
        sed_from_galacticus_mags._mag_norm = sed_data['magNorm']
        sed_from_galacticus_mags._sed_mags = np.array([sed_data['mag%d' % ii]
                                                       for ii in range(30)]).transpose()

    galacticus_colors = np.array([galacticus_mags[ii+1]-galacticus_mags[ii]
                                  for ii in range(29)]).transpose()

    mag_dist, mag_dex = sed_from_galacticus_mags._color_tree.query(galacticus_colors, k=1)

    output_names = sed_from_galacticus_mags._sed_names[mag_dex]

    chosen_mags = sed_from_galacticus_mags._sed_mags[mag_dex]
    galacticus_mags_t = galacticus_mags.transpose()
    d_mag = (galacticus_mags_t - chosen_mags).sum(axis=1)/30.0
    output_mag_norm = sed_from_galacticus_mags._mag_norm[mag_dex] + d_mag
    assert len(output_mag_norm) == len(output_names)
    return output_names, output_mag_norm
