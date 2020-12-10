#!/usr/bin/env python

"""
Add, modify or remove value for root_dir in config file.
root_dir
"""
import os
from argparse import ArgumentParser, RawTextHelpFormatter
from GCRCatalogs import write_to_user_config, remove_root_dir_default

def main():
    usage = """Add, modify or remove a path to be used as root_dir in the package config file. A relative path will be resolved to the corresponding absolute path.

If there already is a path in the config file and --override has not been specified, exit with no action.
"""
    parser = ArgumentParser(description=usage,
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("--root-dir", default=None, help="root_dir path to be stored in config file")
    parser.add_argument("--override", action="store_true",
                        help="New value will replace old value, even if that value was not 'None'")
    parser.add_argument("--remove-path", action="store_true")

    args = parser.parse_args()

    if args.remove_path:
        if args.root_dir is not None:
            print("Conflicting options --root-dir and --remove-path")
            return
        remove_root_dir_default()
    else:
        write_to_user_config({'root_dir' : os.path.abspath(args.root_dir)},
                             overwrite=args.override)
        
    

if __name__ == '__main__':
    main()
    
