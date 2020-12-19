#!/usr/bin/env python

"""
Add, modify or remove value for root_dir in config file.
root_dir
"""
import os
from argparse import ArgumentParser, RawTextHelpFormatter
from GCRCatalogs.user_config import UserConfigManager

def main():

    usage="""Directly manipulate items in user config"""

    parser = ArgumentParser(description=usage,
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("operation", help="Operation to be performed for a particular key",
                        choices=("set", "get", "del"))
    parser.add_argument("key", help="Key on which operation is to be performed")
    parser.add_argument("value", help="Value to use when operation is 'set'",
                        default=None, nargs="?")

    args = parser.parse_args()
    umgr = UserConfigManager()
    
    if args.operation == 'get':
        old = umgr.get(args.key)
        if old:
            print(f"Value of {args.key}: {old}")
        else:
            print(f"{args.key} is not in the user config")
    if args.operation == 'del':
        old = umgr.pop(args.key, None)
        if old:
            print(f"{args.key} deleted from user config")
        else:
            print(f"{args.key} was not in user config")
    if args.operation == 'set':
        if not args.value:
            raise ValueError("Must supply value for 'set' operation")
        else:
            old = umgr.get(args.key)
            umgr[args.key] = args.value
            if old:
                print(f"New value set. Old value was {old}")
            else:
                print(f"New value set. No old value")
    
#     usage = """Add, modify or remove a path to be used as root_dir in the package config file. A relative path will be resolved to the corresponding absolute path.

# If there already is a path in the config file and --override has not been specified, exit with no action.
# """
#     parser = ArgumentParser(description=usage,
#                             formatter_class=RawTextHelpFormatter)
#     parser.add_argument("--root-dir", default=None, help="root_dir path to be stored in config file")
#     ##parser.add_argument("--override", action="store_true",
#     ##                    help="New value will replace old value, even if that value was not 'None'")
#     parser.add_argument("--remove-path", action="store_true",
#                         help="Remove root_dir value from user config file")

#     args = parser.parse_args()

#    # if args.remove_path:
#    #     if args.root_dir is not None:
#    #         print("Conflicting options --root-dir and --remove-path")
#    #         return
#    #     old = remove_root_dir_default()
#    # else:
#    #     if not args.root_dir:
#    #         print("Must specify one of --root-dir, --remove-path")
#    #         return
#    #     #set_root_dir(os.path.abspath(args.root_dir), write_to_config=True,
#    #     #             overwrite=args.override)
#    #     old = set_root_dir(os.path.abspath(args.root_dir), write_to_config=True)
    

if __name__ == '__main__':
    main()
    
