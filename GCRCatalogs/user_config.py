import os
from collections.abc import MutableMapping
import yaml

"""
Utility class for managing user config (a dict) persisted to a yaml file.
"""

all = ['UserConfigManager']


class UserConfigManager(MutableMapping):
    _default_config_filename = "gcr-catalogs.yml"
    _default_config_dirname = "lsstdesc"

    def __init__(self, config_filename=None, config_dirname=None):

        self._config_filename = os.path.basename(config_filename or self._default_config_filename)
        self._config_dirname = os.path.basename(config_dirname or self._default_config_dirname)
        self._user_config_home = self._get_user_config_home()
        self._config_path = os.path.join(self._user_config_home, self._config_dirname, self._config_filename)

    @staticmethod
    def _get_user_config_home():
        if os.getenv("XDG_CONFIG_HOME"):                 # Unix
            return os.getenv("XDG_CONFIG_HOME")
        if os.getenv("LOCALAPPDATA"):                    # Win
            return os.getenv("LOCALAPPDATA")
        return os.path.join(os.path.expanduser("~"), ".config")

    def _write_config(self, config_dict):
        """
        Low-level function to write config_dict to disk
        """
        if not config_dict:
            try:
                os.remove(self._config_path)
            except FileNotFoundError:
                return
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, mode='w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)

    def _load_config(self):
        """
        Low-level function to load config_dict from disk
        """
        try:
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            pass
        return dict()

    def __getitem__(self, key):
        return self._load_config()[key]

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
