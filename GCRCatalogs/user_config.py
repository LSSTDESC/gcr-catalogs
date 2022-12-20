from argparse import ArgumentParser, RawTextHelpFormatter
from .user_config_mgr import UserConfigManager

if __name__ == "__main__":
    description = """Directly manipulate items in user config"""

    parser = ArgumentParser(description=description,
                            prog='GCRCatalogs.user_config',
                            usage='python -m %(prog)s [options]',
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
            print(f"Old value was {old}")
        else:
            print(f"{args.key} was not in user config or its value was None.")
    if args.operation == 'set':
        if not args.value:
            parser.error("Must supply value for 'set' operation")
        else:
            old = umgr.get(args.key)
            umgr[args.key] = args.value
            if old:
                print(f"{args.key} is now set to {args.value}\nOld value was {old}")
            else:
                print(f"{args.key} is now set to {args.value}\nNo old value or old value was None")
