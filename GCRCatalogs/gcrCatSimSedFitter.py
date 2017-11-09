import numpy as np
import os

from lsst.utils import getPackageDir
from lsst.sims.photUtils import CosmologyObject

__all__ = ["sed_from_galacticus_mags"]


def sed_from_galacticus_mags(galacticus_mags, redshift, h=0.71, omega_m=0.265):
    """
    galacticus_mags is a numpy array such that
    galacticus_mags[i][j] is the magnitude of the jth star in the ith bandpass,
    where the bandpasses are ordered in ascending order of minimum wavelength.

    Will return a numpy array of SED names and a numpy array of magNorms.
    """

    if not hasattr(sed_from_galacticus_mags, '_sed_color_tree'):
        catsim_dir = os.path.join(getPackageDir('gcr_catalogs'),
                                  'CatSimSupport')
        color_grid_file = os.path.join(catsim_dir, 'CatSimMagGrid.txt')

        if not os.path.exists(color_grid_file):
            msg = '\n%s does not exist\n' % color_grid_file
            msg += 'Go into the directory %s ' % catsim_dir
            msg += 'and run the script get_sed_mags.py'
            raise RuntimeError(msg)

        dtype_list = [('name', str, 200)]
        for ii in range(30):
            dtype_list.append(('mag%d' % ii, float))
        dtype_list.append(('magNorm', float))
        dtype = np.dtype(dtype_list)
        sed_data = np.genfromtxt(color_grid_file, dtype=dtype)
        sed_colors = np.array([sed_data['mag%d' % (ii+1)] - sed_data['mag%d' % ii]
                               for ii in range(29)])
        sed_from_galacticus_mags._sed_colors = sed_colors.transpose()
        sed_from_galacticus_mags._sed_names = sed_data['name']
        sed_from_galacticus_mags._mag_norm = sed_data['magNorm']
        sed_from_galacticus_mags._sed_mags = np.array([sed_data['mag%d' % ii]
                                                       for ii in range(30)]).transpose()

    cosmology = CosmologyObject(H0=100.0*h, Om0=omega_m)
    distance_modulus = cosmology.distanceModulus(redshift=redshift)
    assert len(distance_modulus) == len(galacticus_mags[0])

    galacticus_colors = np.array([galacticus_mags[ii+1]-galacticus_mags[ii]
                                  for ii in range(29)]).transpose()

    out_color_dist = np.zeros(len(galacticus_colors), dtype=float)
    mag_dex = np.zeros(len(galacticus_colors), dtype=int)
    for i_star in range(len(galacticus_colors)):
        dd = np.sum((galacticus_colors[i_star]
                     -sed_from_galacticus_mags._sed_colors)**2, axis=1)
        mag_dex[i_star] = np.argmin(dd)
        out_color_dist[i_star] = dd[mag_dex[i_star]]

    output_names = sed_from_galacticus_mags._sed_names[mag_dex]

    chosen_mags = sed_from_galacticus_mags._sed_mags[mag_dex]
    galacticus_mags_t = galacticus_mags.transpose()
    d_mag = (galacticus_mags_t - chosen_mags).sum(axis=1)/30.0
    output_mag_norm = sed_from_galacticus_mags._mag_norm[mag_dex] + d_mag + distance_modulus
    assert len(output_mag_norm) == len(output_names)
    normed_mags = np.array([chosen_mags[ii] + d_mag[ii] for ii in range(len(d_mag))])
    out_mag_dist = np.sqrt(((galacticus_mags_t - normed_mags)**2).sum(axis=1))
    assert len(out_mag_dist) == len(output_names)

    return output_names, output_mag_norm, out_color_dist, out_mag_dist
