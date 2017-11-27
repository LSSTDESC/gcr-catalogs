import numpy as np
import os

from GCRCatalogs import load_catalog
from GCRCatSimInterface import sed_from_galacticus_mags

from lsst.utils import getPackageDir

step_to_z ={}
step_to_z[499]=0.0
step_to_z[487]=0.0245
step_to_z[475]=0.0502
step_to_z[464]=0.0749
step_to_z[453]=0.1008
step_to_z[442]=0.1279
step_to_z[432]=0.1538
step_to_z[421]=0.1837
step_to_z[411]=0.2123
step_to_z[401]=0.2423
step_to_z[392]=0.2705
step_to_z[382]=0.3035
step_to_z[373]=0.3347
step_to_z[365]=0.3636
step_to_z[355]=0.4017
step_to_z[347]=0.4337
step_to_z[338]=0.4714
step_to_z[331]=0.5022
step_to_z[323]=0.5391
step_to_z[315]=0.5777
step_to_z[307]=0.6184
step_to_z[300]=0.6557
step_to_z[293]=0.6948
step_to_z[286]=0.7358
step_to_z[279]=0.7788
step_to_z[272]=0.8240
step_to_z[266]=0.8646
step_to_z[259]=0.9143
step_to_z[253]=0.9591
step_to_z[247]=1.0060
step_to_z[241]=1.0552
step_to_z[235]=1.1069


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
qty_names.append('step')

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

u_rest_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_u:rest'][first_disk]
g_rest_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_g:rest'][first_disk]
r_rest_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_r:rest'][first_disk]
i_rest_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_i:rest'][first_disk]
z_rest_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_z:rest'][first_disk]
y_rest_dustless = catalog_qties['LSST_filters/diskLuminositiesStellar:LSST_y:rest'][first_disk]

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

# hack to use the redshift at the snapshot of the galaxy
true_redshift_list = []
for step in catalog_qties['step'][first_disk]:
    true_redshift_list.append(step_to_z[step])
true_redshift_list = np.array(true_redshift_list)
full_redshift_list = true_redshift_list


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

u_rest_dustless = u_rest_dustless[av_valid]
g_rest_dustless = g_rest_dustless[av_valid]
r_rest_dustless = r_rest_dustless[av_valid]
i_rest_dustless = i_rest_dustless[av_valid]
z_rest_dustless = z_rest_dustless[av_valid]
y_rest_dustless = y_rest_dustless[av_valid]

ct = 0
print(sed_name_list)

out_file = open('Rv_vs_magdist.txt', 'w')
out_file.write('# Rv Av EBV d du dg... du_dustless dg_dustless... du_rest_dustless dg_rest_dustless...\n')

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

    udlrest = u_rest_dustless[i_star]
    gdlrest = g_rest_dustless[i_star]
    rdlrest = r_rest_dustless[i_star]
    idlrest = i_rest_dustless[i_star]
    zdlrest = z_rest_dustless[i_star]
    ydlrest = y_rest_dustless[i_star]

    dustless = Sed()
    sed = Sed()
    rest_sed_dustless = Sed()

    full_sed_name = os.path.join(gal_sed_dir, sed_name)
    sed.readSED_flambda(full_sed_name)
    dustless.readSED_flambda(full_sed_name)
    rest_sed_dustless.readSED_flambda(full_sed_name)

    f_norm = getImsimFluxNorm(sed, mag_norm)
    sed.multiplyFluxNorm(f_norm)
    dustless.multiplyFluxNorm(f_norm)
    rest_sed_dustless.multiplyFluxNorm(f_norm)

    a_x, b_x = sed.setupCCMab()
    R_v = av/ebv
    sed.addCCMDust(a_x, b_x, ebv=ebv, R_v=R_v)

    sed.redshiftSED(full_redshift, dimming=True)
    dustless.redshiftSED(full_redshift, dimming=True)

    mag_list = lsst_bp_dict.magListForSed(sed)
    dustless_list = lsst_bp_dict.magListForSed(dustless)
    rest_dustless_list = lsst_bp_dict.magListForSed(rest_sed_dustless)

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

    out_file.write('%e ' % (rest_dustless_list[0]-udlrest))
    out_file.write('%e ' % (rest_dustless_list[1]-gdlrest))
    out_file.write('%e ' % (rest_dustless_list[2]-rdlrest))
    out_file.write('%e ' % (rest_dustless_list[3]-idlrest))
    out_file.write('%e ' % (rest_dustless_list[4]-zdlrest))
    out_file.write('%e ' % (rest_dustless_list[5]-ydlrest))


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
