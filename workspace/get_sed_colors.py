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
bp_list = []
wav_grid = np.arange(wav_min, wav_max, 0.1)
sb_baseline = np.ones(len(wav_grid), dtype=float)
for wav_params in bp_params_dict['disk']:
    wav0 = 0.1*wav_params[0]
    wav_width = 0.1*wav_params[1]
    sb_grid = np.where(np.logical_and(wav_grid>=wav0, wav_grid<=wav0+wav_width),
                       sb_baseline, 0.0)

    bp = Bandpass(wavelen=wav_grid, sb=sb_grid)
    bp_name_list.append(wav0)
    bp_list.append(bp)

bp_name_list = np.array(bp_name_list)
bp_list = np.array(bp_list)

sorted_dex = np.argsort(bp_name_list)
bp_name_list = bp_name_list[sorted_dex]
bp_list = bp_list[sorted_dex]

bp_dict = BandpassDict(bp_list, bp_name_list)

from lsst.sims.photUtils import Sed


