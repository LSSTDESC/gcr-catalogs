import os
import warnings
import yaml

"""
Utility class for managing user config (a dict) persisted to a yaml file. 
"""

all = ['UserConfigManager']

def _load_yaml_local(yaml_file):
    with open(yaml_file) as f:
        return yaml.safe_load(f)

class UserConfigManager():
    def __init__(self, config_name):
        self._config_name = config_name

        def _get_config_dir(create=True):
            if os.getenv("XDG_CONFIG_HOME"):                   # Unix
                user_config_dir = os.getenv("XDG_CONFIG_HOME")	
            elif os.getenv("LOCALAPPDATA"):                     # Win
                user_config_dir = os.getenv("LOCALAPPDATA")
            else:
                user_config_dir = os.path.join(os.path.expanduser("~"), ".config")

            desc_config_dir = os.path.join(user_config_dir, "lsstdesc")

            if create:
                os.makedirs(desc_config_dir, exist_ok=True)

            return desc_config_dir
            
        self._config_path = os.path.join(_get_config_dir(), config_name)


    def user_config_exists(self):
        return os.path.exists(self._config_path)

    
    def write_entries(self, entries, overwrite=False):
        """
        Write one or more key-value pairs to the config file.  Create new file or
        append to existing file. 

        Parameters
        ----------
        entries     dict of entries to be written to file
        overwrite   boolean.  If new keys overlap with old and overwrite is False, do
                    nothing.  If True, new values prevail.

        Returns
        -------
        dict written to the file.  
        If overwrite condition is violated, return None

        """
        config_dict = {}

        if self.user_config_exists():
            config_dict = _load_yaml_local(self._config_path)
            if not overwrite:
                if not config_dict.keys().isdisjoint(entries.keys()):
                    warnings.warn("Overwrite condition violated; config file not updated")
                    return None

        config_dict.update(entries)

        with open(self._config_path, mode='w') as f:
            f.write(yaml.dump(config_dict, default_flow_style=False))

        return config_dict

    
    def remove_keys(self, keys):
        """
        Remove entries from config file

        Parameters
        ----------
        A collection of keys
        """

        if not self.user_config_exists():
            return

        config_dict = _load_yaml_local(self._config_path)
        for k in keys:
            if k in config_dict.keys():
                del config_dict[k]

        if len(config_dict) == 0:
            os.remove(self._config_path)
        else:
            with open(self._config_path, mode='w') as f:
                f.write(yaml.dump(config_dict, default_flow_style=False))


    def get_value(self, key):
        if not self.user_config_exists():
            return None
        
        config_dict = _load_yaml_local(self._config_path)
        if key in config_dict:
            return config_dict[key]
        else:
            return None
    
