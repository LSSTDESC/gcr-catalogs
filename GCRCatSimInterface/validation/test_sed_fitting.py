import numpy as np
import os

from GCRCatalogs import load_catalog
from GCRCatSimInterface import sed_from_galacticus_mags

from lsst.utils import getPackageDir

catalog = load_catalog('proto-dc2_v2.0')

qty_names = []
with open(os.path.join(getPackageDir('gcr_catalogs'), 'GCRCatSimInterface',
          'data', 'CatSimMagGrid.txt'), 'r') as in_file:
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
qty_names.append('redshift_true')
qty_names.append('redshift')

for filter_name in ('u', 'g', 'r', 'i', 'z', 'y'):
    qty_names.append('LSST_filters/diskLuminositiesStellar:LSST_%s:observed:dustAtlas' % filter_name)
    qty_names.append('LSST_filters/spheroidLuminositiesStellar:LSST_%s:observed:dustAtlas' % filter_name)

    qty_names.append('LSST_filters/diskLuminositiesStellar:LSST_%s:observed' % filter_name)
    qty_names.append('LSST_filters/spheroidLuminositiesStellar:LSST_%s:observed' % filter_name)



qty_names.append('otherLuminosities/diskLuminositiesStellar:V:rest')
qty_names.append('otherLuminosities/diskLuminositiesStellar:V:rest:dustAtlas')
qty_names.append('otherLuminosities/diskLuminositiesStellar:B:rest')
qty_names.append('otherLuminosities/diskLuminositiesStellar:B:rest:dustAtlas')

qty_names.append('otherLuminosities/spheroidLuminositiesStellar:V:rest')
qty_names.append('otherLuminosities/spheroidLuminositiesStellar:V:rest:dustAtlas')
qty_names.append('otherLuminosities/spheroidLuminositiesStellar:B:rest')
qty_names.append('otherLuminosities/spheroidLuminositiesStellar:B:rest:dustAtlas')

catalog_qties = catalog.get_quantities(qty_names)

has_disk = np.where(catalog_qties[disk_mag_names[0]]>0.0)
has_bulge = np.where(catalog_qties[bulge_mag_names[0]]>0.0)

#first_disk = has_disk[0]

rng = np.random.RandomState(812351233)
first_disk = rng.choice(has_disk[0], size=100000, replace=False)

disk_mags = np.array([-2.5*np.log10(catalog_qties[name][first_disk]) for name in disk_mag_names])

u_control = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_u:observed:dustAtlas'][first_disk]
g_control = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_g:observed:dustAtlas'][first_disk]
r_control = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_r:observed:dustAtlas'][first_disk]
i_control = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_i:observed:dustAtlas'][first_disk]
z_control = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_z:observed:dustAtlas'][first_disk]
y_control = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_y:observed:dustAtlas'][first_disk]

u_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_u:observed'][first_disk]
g_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_g:observed'][first_disk]
r_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_r:observed'][first_disk]
i_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_i:observed'][first_disk]
z_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_z:observed'][first_disk]
y_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_y:observed'][first_disk]



ebv_list = -2.5*(np.log10(catalog_qties['otherLuminosities/diskLuminositiesStellar:B:rest:dustAtlas']) -
            np.log10(catalog_qties['otherLuminosities/diskLuminositiesStellar:V:rest:dustAtlas']) -
            np.log10(catalog_qties['otherLuminosities/diskLuminositiesStellar:B:rest']) +
            np.log10(catalog_qties['otherLuminosities/diskLuminositiesStellar:V:rest']))

av_list = -2.5*(np.log10(catalog_qties['otherLuminosities/diskLuminositiesStellar:V:rest:dustAtlas']) -
           np.log10(catalog_qties['otherLuminosities/diskLuminositiesStellar:V:rest']))

ebv_list = ebv_list[first_disk]
av_list = av_list[first_disk]

true_redshift_list =  catalog_qties['redshift_true'][first_disk]
full_redshift_list = catalog_qties['redshift'][first_disk]

from lsst.sims.photUtils import CosmologyObject
cosmo = CosmologyObject(H0=71.0, Om0=0.265)

dm = cosmo.distanceModulus(true_redshift_list)

fudge = 2.5*np.log10(1.0+true_redshift_list)

u_control = -2.5*np.log10(u_control) + dm - fudge
g_control = -2.5*np.log10(g_control) + dm - fudge
r_control = -2.5*np.log10(r_control) + dm - fudge
i_control = -2.5*np.log10(i_control) + dm - fudge
z_control = -2.5*np.log10(z_control) + dm - fudge
y_control = -2.5*np.log10(y_control) + dm - fudge

u_dustless = -2.5*np.log10(u_dustless) + dm - fudge
g_dustless = -2.5*np.log10(g_dustless) + dm - fudge
r_dustless = -2.5*np.log10(r_dustless) + dm - fudge
i_dustless = -2.5*np.log10(i_dustless) + dm - fudge
z_dustless = -2.5*np.log10(z_dustless) + dm - fudge
y_dustless = -2.5*np.log10(y_dustless) + dm - fudge

import time
t_start = time.time()
sed_name_list, mag_norm_list = sed_from_galacticus_mags(disk_mags, true_redshift_list)
print("fitting %d took %.3e" % (len(sed_name_list), time.time()-t_start))
print("mag norm %e %e %e" % (mag_norm_list.min(), np.median(mag_norm_list), mag_norm_list.max()))
assert len(sed_name_list) == len(first_disk)

sed_dir = getPackageDir('sims_sed_library')
gal_sed_dir = os.path.join(sed_dir, 'galaxySED')

from  lsst.sims.photUtils import Sed, BandpassDict, getImsimFluxNorm

total_bp_dict, lsst_bp_dict = BandpassDict.loadBandpassesFromFiles()

worst_dist = -1.0

av_valid = np.where(np.logical_and(av_list>0.01, np.logical_and(ebv_list>0.0, av_list<5.0)))
sed_name_list = sed_name_list[av_valid]
mag_norm_list = mag_norm_list[av_valid]
true_redshift_list = true_redshift_list[av_valid]
full_redshift_list = full_redshift_list[av_valid]
av_list = av_list[av_valid]
ebv_list = ebv_list[av_valid]
u_control = u_control[av_valid]
g_control = g_control[av_valid]
r_control = r_control[av_valid]
i_control = i_control[av_valid]
z_control = z_control[av_valid]
y_control = y_control[av_valid]
u_dustless = u_dustless[av_valid]
g_dustless = g_dustless[av_valid]
r_dustless = r_dustless[av_valid]
i_dustless = i_dustless[av_valid]
z_dustless = z_dustless[av_valid]
y_dustless = y_dustless[av_valid]


ct = 0
print(sed_name_list)

out_file = open('Rv_vs_magdist.txt', 'w')
out_file.write('# Rv Av EBV d du dg dr di dz dy du_dustless dg_dustless...\n')

for i_star in range(len(sed_name_list)):
    sed_name = sed_name_list[i_star]
    mag_norm = mag_norm_list[i_star]
    true_redshift = true_redshift_list[i_star]
    full_redshift = full_redshift_list[i_star]
    av = av_list[i_star]
    ebv = ebv_list[i_star]
    uu = u_control[i_star]
    gg = g_control[i_star]
    rr = r_control[i_star]
    ii = i_control[i_star]
    zz = z_control[i_star]
    yy = y_control[i_star]
    udl = u_dustless[i_star]
    gdl = g_dustless[i_star]
    rdl = r_dustless[i_star]
    idl = i_dustless[i_star]
    zdl = z_dustless[i_star]
    ydl = y_dustless[i_star]

    dustless = Sed()
    sed = Sed()
    sed.readSED_flambda(os.path.join(gal_sed_dir, sed_name))
    dustless.readSED_flambda(os.path.join(gal_sed_dir, sed_name))
    f_norm = getImsimFluxNorm(sed, mag_norm)
    sed.multiplyFluxNorm(f_norm)
    dustless.multiplyFluxNorm(f_norm)
    a_x, b_x = sed.setupCCMab()
    R_v = av/ebv
    sed.addCCMDust(a_x, b_x, ebv=ebv, R_v=R_v)
    sed.redshiftSED(full_redshift, dimming=True)
    dustless.redshiftSED(full_redshift, dimming=True)
    mag_list = lsst_bp_dict.magListForSed(sed)
    dustless_list = lsst_bp_dict.magListForSed(dustless)

    dd = 0.0
    dd += (mag_list[0] - uu)**2
    dd += (mag_list[1] - gg)**2
    dd += (mag_list[2] - rr)**2
    dd += (mag_list[3] - ii)**2
    dd += (mag_list[4] - zz)**2
    dd += (mag_list[5] - yy)**2
    dd = np.sqrt(dd)

    out_file.write('%e %e %e %e ' % (av/ebv, av, ebv, dd))
    out_file.write('%e ' % (mag_list[0]-uu))
    out_file.write('%e ' % (mag_list[1]-gg))
    out_file.write('%e ' % (mag_list[2]-rr))
    out_file.write('%e ' % (mag_list[3]-ii))
    out_file.write('%e ' % (mag_list[4]-zz))
    out_file.write('%e ' % (mag_list[5]-yy))

    out_file.write('%e ' % (dustless_list[0]-udl))
    out_file.write('%e ' % (dustless_list[1]-gdl))
    out_file.write('%e ' % (dustless_list[2]-rdl))
    out_file.write('%e ' % (dustless_list[3]-idl))
    out_file.write('%e ' % (dustless_list[4]-zdl))
    out_file.write('%e ' % (dustless_list[5]-ydl))

    out_file.write('\n')


    if dd > worst_dist:
        print('\nworst mag dist %.3e -- magnorm %.3e ebv %.3e av %.3e' % (dd,mag_norm,ebv,av))
        print('redshift %e' % (true_redshift))
        for i_filter, (cc, ccdl) in enumerate(zip((uu, gg, rr, ii, zz, yy), (udl, gdl, rdl, idl, zdl, ydl))):
            dust_model = mag_list[i_filter] - dustless_list[i_filter]
            dust_gal = cc - ccdl
            worst_dist = dd
            print('    model %e truth %e diff %e dust_diff %e' %
                  (mag_list[i_filter],
                   cc,
                   cc-mag_list[i_filter],
                   dust_gal-dust_model))

out_file.close()
exit()

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


exit()
#### now do bulges
print('bulges')

first_bulge = has_bulge[0][:10000]

bulge_mags = np.array([-2.5*np.log10(catalog_qties[name][first_bulge]) for name in bulge_mag_names])

t_start = time.time()
sed_names, mag_norms = sed_from_galacticus_mags(bulge_mags, catalog_qties['redshift_true'][first_bulge])
print("fitting %d took %.3e" % (len(sed_names), time.time()-t_start))
print("mag norm %e %e %e\n" % (mag_norms.min(), np.median(mag_norms), mag_norms.max()))
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
