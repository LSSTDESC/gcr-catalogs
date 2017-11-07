bp_dict = {}
bp_dict['disk'] = []
bp_dict['bulge'] = []

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
        bp_dict[tag].append((wav0, width))

assert len(bp_dict['disk']) >0
assert len(bp_dict['bulge']) > 0
assert len(bp_dict['bulge']) == len(bp_dict['disk'])
print('len %d' % len(bp_dict['disk']))

for bp in bp_dict['disk']:
    assert bp in bp_dict['bulge']

