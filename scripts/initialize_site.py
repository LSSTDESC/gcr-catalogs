#!/usr/bin/env python

"""
Initialize path for local_user site
"""
import os
import yaml
from datetime import datetime
from argparse import ArgumentParser, RawTextHelpFormatter


all = ['set_local_site_path']

_HERE = os.path.dirname(__file__)
_SITE_FILE_PATH = os.path.join(_HERE, '..', 'GCRCatalogs', 'site_config','site_rootdir.yaml')

def set_local_site_path(root_dir, override=False):
    print(f'Called with values root_dir={root_dir}, override={override}')
    print(_SITE_FILE_PATH)

    with open(_SITE_FILE_PATH) as f:
        site_dict = yaml.safe_load(f)

    # If root_dir isn't an absolute path, resolve it to one
    root_dir = os.path.abspath(root_dir)

    if 'local_user' in site_dict:
        old = site_dict['local_user']
    
        if (old !=  'None') and not override:
            print(f'Use --override flag to overwrite old value {old}')
            return

    site_dict['local_user'] = root_dir

    print('Write to new file')
    new_file = _SITE_FILE_PATH + '.new'
    now = datetime.now().isoformat()
    with open(new_file, mode='w') as f:
        f.write(yaml.dump(site_dict, default_flow_style=False))
        f.write(f'# last updated {now}\n')

    os.rename(new_file, _SITE_FILE_PATH)
    
    return
        
    
        

def main():
    usage = """Specify a path to be associated with the site 'local_user'. A relative path will be resolved to the corresponding absolute path. Unless overridden by the environment variable DESC_GCR_SITE, GCRCatalogs will search for catalogs relative to this path.

If there already is a path associated with 'local_user' and --override has not been specified, exit with no action.
"""
    parser = ArgumentParser(description=usage,
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("root_dir", help="Path to be associated with site 'local_user'")
    parser.add_argument("--override", action="store_true",
                        help="New value will replace old value, even if that value was not 'None'")
    set_local_site_path(**vars(parser.parse_args()))

if __name__ == '__main__':
    main()
    
