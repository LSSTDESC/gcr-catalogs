import numpy as np
import os

from GCRCatalogs import load_catalog
from GCRCatalogs import sed_from_galacticus_mags

from lsst.utils import getPackageDir

catalog = load_catalog('proto-dc2_v2.0')

qty_names = []
with open(os.path.join(getPackageDir('gcr_catalogs'), 'CatSimSupport', 'CatSimMagGrid.txt'), 'r') as in_file:
    header = in_file.readlines()[0]

header = header.strip().split()
disk_mag_names = []
bulge_mag_names = []

for name in header[2:-1]:
    disk_mag_names.append('SEDs/diskLuminositiesStellar:SED_%s:rest' % name)
    bulge_mag_names.append('SEDs/spheroidLuminositiesStellar:SED_%s:rest' % name)

for name in disk_mag_names:
    qty_names.append(name)

for name in bulge_mag_names:
    qty_names.append(name)

qty_names.append('morphology/diskRadiusArcsec')
qty_names.append('morphology/spheroidRadiusArcsec')

catalog_qties = catalog.get_quantities(qty_names)

has_disk = np.where(catalog_qties[disk_mag_names[0]]>0.0)
has_bulge = np.where(catalog_qties[bulge_mag_names[0]]>0.0)

first_disk = has_disk[0][:10000]

disk_mags = np.array([-2.5*np.log10(catalog_qties[name][first_disk]) for name in disk_mag_names])

import time
t_start = time.time()
sed_names, mag_norms = sed_from_galacticus_mags(disk_mags)
print("fitting %d took %.3e" % (len(sed_names), time.time()-t_start))
assert len(sed_names) == len(first_disk)


dtype_list = [('name', str, 200)]
for ii in range(30):
    dtype_list.append(('mag%d' % ii, float))
dtype_list.append(('magNorm', float))


catsim_name = os.path.join(getPackageDir('gcr_catalogs'), 'CatSimSupport',
                           'CatSimMagGrid.txt')

dtype = np.dtype(dtype_list)

sed_data = np.genfromtxt(catsim_name, dtype=dtype)

worst_dist = -1.0
for i_star in range(len(sed_names)):
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
        dist += (disk_mags[i_mag][i_star] - sed_data['mag%d' % i_mag][chosen_sed] - d_mag)**2
    dist = np.sqrt(dist)
    if dist> worst_dist:
        model_colors = np.array([disk_mags[ii+1][i_star] - disk_mags[ii][i_star] for ii in range(29)])
        sed_colors = np.array([sed_data['mag%d' % (ii+1)][chosen_sed] - sed_data['mag%d' % ii][chosen_sed]
                               for ii in range(29)])
        d_color = np.sqrt(np.sum((model_colors-sed_colors)**2))
        worst_dist = dist
        print('worst_dist %e -- %e' % (worst_dist, d_color))
        for i_mag in range(30):
            if i_mag==0:
                print('    ',end='')
            print('%.3e ' % (disk_mags[i_mag][i_star]-sed_data['mag%d' % i_mag][chosen_sed]-d_mag), end='')
            if i_mag%5==0 and i_mag>0:
                print('\n    ',end='')

        print('\n',end='')

#### now do bulges
print('bulges')

first_bulge = has_bulge[0][:10000]

bulge_mags = np.array([-2.5*np.log10(catalog_qties[name][first_bulge]) for name in bulge_mag_names])

import time
t_start = time.time()
sed_names, mag_norms = sed_from_galacticus_mags(bulge_mags)
print("fitting %d took %.3e" % (len(sed_names), time.time()-t_start))
assert len(sed_names) == len(first_bulge)


dtype_list = [('name', str, 200)]
for ii in range(30):
    dtype_list.append(('mag%d' % ii, float))
dtype_list.append(('magNorm', float))


catsim_name = os.path.join(getPackageDir('gcr_catalogs'), 'CatSimSupport',
                           'CatSimMagGrid.txt')

dtype = np.dtype(dtype_list)

sed_data = np.genfromtxt(catsim_name, dtype=dtype)

worst_dist = -1.0
for i_star in range(len(sed_names)):
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
        dist += (bulge_mags[i_mag][i_star] - sed_data['mag%d' % i_mag][chosen_sed] - d_mag)**2
    dist = np.sqrt(dist)
    if dist> worst_dist:
        model_colors = np.array([bulge_mags[ii+1][i_star] - bulge_mags[ii][i_star] for ii in range(29)])
        sed_colors = np.array([sed_data['mag%d' % (ii+1)][chosen_sed] - sed_data['mag%d' % ii][chosen_sed]
                               for ii in range(29)])
        d_color = np.sqrt(np.sum((model_colors-sed_colors)**2))
        worst_dist = dist
        print('worst_dist %e -- %e' % (worst_dist, d_color))
