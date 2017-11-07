import numpy as np
import os

rng = np.random.RandomState(8123)

n_stars = 1000
n_mags = 30

random_mags = rng.random_sample((n_mags, n_stars))

from GCRCatalogs import sed_from_galacticus_mags

sed_names, mag_norms = sed_from_galacticus_mags(random_mags)

dtype_list = [('name', str, 200)]
for ii in range(30):
    dtype_list.append(('mag%d' % ii, float))
dtype_list.append(('magNorm', float))

from lsst.utils import getPackageDir

catsim_name = os.path.join(getPackageDir('gcr_catalogs'), 'CatSimSupport',
                           'CatSimMagGrid.txt')

dtype = np.dtype(dtype_list)

sed_data = np.genfromtxt(catsim_name, dtype=dtype)

worst_dist = -1.0
for i_star in range(n_stars):
    chosen_sed = None
    for i_sed in range(len(sed_data)):
        if sed_data['name'][i_sed] == sed_names[i_star]:
            chosen_sed = i_sed
            break
    if chosen_sed is None:
        raise RuntimeError("Could not find sed %s" % sed_name[i_star])
    
    d_mag = mag_norms[i_star] - sed_data['magNorm'][chosen_sed]

    dist = 0.0
    for i_mag in range(30):
        dist += (random_mags[i_mag][i_star] - sed_data['mag%d' % i_mag][chosen_sed] - d_mag)**2
    dist = np.sqrt(dist)
    if dist> worst_dist:
        worst_dist = dist
        print('worst_dist %e' % worst_dist)
