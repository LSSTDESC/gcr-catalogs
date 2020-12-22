import os
import yaml
from collections.abc import MutableMapping

"""
Utility class for managing user config (a dict) persisted to a yaml file.
"""

__all__ = ['UserConfigManager']


class UserConfigManager(MutableMapping):
    _default_config_filename = "gcr-catalogs.yaml"
    _default_config_reldir = "lsstdesc"

    def __init__(self, config_filename=None, config_reldir=None):
        config_name = os.path.basename(config_filename or self._default_config_filename)
        reldir = config_reldir or self._default_config_reldir
        if os.path.isabs(reldir):
            raise ValueError(f'{reldir} must be a relative path')
        self._user_config_dir = os.path.join(self._get_config_home(), reldir)
        self._user_config_path = os.path.join(self._user_config_dir, config_name)

    @staticmethod
    def _get_config_home():
        if os.getenv("XDG_CONFIG_HOME"):                   # Unix
            return(os.getenv("XDG_CONFIG_HOME"))
        elif os.getenv("LOCALAPPDATA"):                     # Win
            return(os.getenv("LOCALAPPDATA"))

        return os.path.join(os.path.expanduser("~"), ".config")

    # Override methods which may access more than one item for efficiency
    def keys(self):
        return self._load_config().keys()

    def values(self):
        return self._load_config().values()

    def items(self):
        return self._load_config().items()

    def update(self, items):
        """
        Write one or more key-value pairs to the config file.  Create new file or
        append to existing file.

        Parameters
        ----------
        items       dict of entries to be written to file

        Returns
        -------
        dict written to the file.
        If overwrite condition is violated, raise ValueError

        """
        config_dict = self._load_config()

        config_dict.update(items)
        return self._write_config(config_dict)

    def clear(self):
        return self._write_config(dict())

    def deleteitems(self, keys, absent_ok=True):
        """
        Remove specified items from config file

        Parameters
        ----------
        A collection of keys
        """

        config_dict = self._load_config()

        if not absent_ok and not all(key in config_dict for key in keys):
            raise KeyError("Some keys do not exist")

        for key in keys:
            config_dict.pop(key, None)

        return self._write_config(config_dict)

    def _user_config_exists(self):
        return os.path.exists(self._user_config_path)

    def _write_config(self, config_dict):
        os.makedirs(self._user_config_dir, exist_ok=True)
        if not config_dict:
            config_dict = dict()

        with open(self._user_config_path, mode='w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
        return config_dict

    def _load_config(self):
        if not self._user_config_exists():
            return dict()

        with open(self._user_config_path) as f:
            return yaml.safe_load(f)

    def __getitem__(self, key):
        config_dict = self._load_config()
        return config_dict[key]

    def __setitem__(self, key, value):
        config_dict = self._load_config()
        config_dict[key] = value
        self._write_config(config_dict)

    def __delitem__(self, key):
        config_dict = self._load_config()
        del config_dict[key]
        self._write_config(config_dict)

    def __iter__(self):
        return iter(self._load_config())

    def __len__(self):
        return len(self._load_config())
