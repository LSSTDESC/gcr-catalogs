bp_params_dict = {}
bp_params_dict['disk'] = []
bp_params_dict['bulge'] = []

with open('dc2_seds.txt', 'r') as input_file:
    for line in input_file:
        if 'dustAtlas' in line:
            continue
        params = line.strip()
        params = params.replace('/', '|')
        params = params.replace(':', '|')
        params = params.replace('_', '|')
        params = params.split('|')
        if 'disk' in params[1]:
            tag = 'disk'
        elif 'spheroid'in params[1]:
            tag = 'bulge'
        else:
            continue

        wav0 = int(params[3])
        width= int(params[4])
        bp_params_dict[tag].append((wav0, width))

assert len(bp_params_dict['disk']) >0
assert len(bp_params_dict['bulge']) > 0
assert len(bp_params_dict['bulge']) == len(bp_params_dict['disk'])
print('len %d' % len(bp_params_dict['disk']))

for bp in bp_params_dict['disk']:
    assert bp in bp_params_dict['bulge']

import numpy as np
from lsst.sims.photUtils import BandpassDict, Bandpass

imsim_bp = Bandpass()
imsim_bp.imsimBandpass()

wav_min = 1.0e30
wav_max = -1.0e30
for wav_params in bp_params_dict['disk']:
    wav0 = 0.1*wav_params[0]
    wav1 = wav0+0.1*wav_params[1]
    if wav0<wav_min:
        wav_min = wav0
    if wav1>wav_max:
        wav_max = wav1

bp_name_list = []
bp_min_list = []
bp_list = []
wav_grid = np.arange(wav_min, wav_max, 0.1)
sb_baseline = np.ones(len(wav_grid), dtype=float)
for wav_params in bp_params_dict['disk']:
    wav0 = 0.1*wav_params[0]
    wav_width = 0.1*wav_params[1]
    sb_grid = np.where(np.logical_and(wav_grid>=wav0, wav_grid<=wav0+wav_width),
                       sb_baseline, 0.0)

    bp = Bandpass(wavelen=wav_grid, sb=sb_grid)
    bp_name_list.append('%d_%d' % (wav_params[0], wav_params[1]))
    bp_min_list.append(wav_params[0])
    bp_list.append(bp)

bp_name_list = np.array(bp_name_list)
bp_list = np.array(bp_list)
bp_min_list = np.array(bp_min_list)

sorted_dex = np.argsort(bp_min_list)
bp_min_list = bp_min_list[sorted_dex]
bp_name_list = bp_name_list[sorted_dex]
bp_list = bp_list[sorted_dex]

bp_dict = BandpassDict(bp_list, bp_name_list)

import os
from lsst.utils import getPackageDir
from lsst.sims.photUtils import Sed

galaxy_sed_dir = os.path.join(getPackageDir('sims_sed_library'), 'galaxySED')
sed_file_list = os.listdir(galaxy_sed_dir)

with open('CatSimMagGrid.txt', 'w') as out_file:
    out_file.write('# sed_name ')
    for bp_name in bp_dict:
        out_file.write('%s ' % bp_name)
    out_file.write('magNorm\n')
    for file_name in sed_file_list:
        full_name = os.path.join(galaxy_sed_dir, file_name)
        spec = Sed()
        spec.readSED_flambda(full_name)
        mag_list = bp_dict.magListForSed(spec)
        mag_norm = spec.calcMag(imsim_bp)
        out_file.write('%s ' % file_name)
        for i_filter in range(len(bp_dict)):
            out_file.write('%.6g ' % mag_list[i_filter])
        out_file.write('%.6g\n' % mag_norm)

