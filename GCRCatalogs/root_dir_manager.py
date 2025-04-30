import os
import warnings
from .user_config_mgr import UserConfigManager
from .catalog_helpers import load_yaml_local
from .utils import is_string_like

_DESC_SITE_ENV = "DESC_GCR_SITE"

def get_site_name():
    """
        Return a string which, when executing at a recognized site with
        well-known name, will include the name for that site
        """

    site_from_env = os.getenv(_DESC_SITE_ENV, "")
    if site_from_env:
        return site_from_env

    if os.getenv("NERSC_HOST", ""):
        site_from_node = 'nersc'
    else:
        site_from_node = None
    return site_from_node


class RootDirManager:
    _ROOT_DIR_SIGNAL = "^/"
    _ROOT_DIR_KEY = "root_dir"
    _PATH_LIKE_KEYS = (
        "filename",
        "addon_filename",
        "base_dir",
        "root_dir",
        "catalog_root_dir",
        "header_file",
        "repo",
        "table_dir",
        "meta_path",
    )
    _DICT_LIST_KEYS = ("catalogs",)
    _NO_DEFAULT_ROOT_WARN = """
       Default root dir has not been set; catalogs may not be found.

       For DESC users:
       You can specify the site as an environment variable before you import
       GCRCatalogs,
            $ export {}='sitename'
       or, from within Python and after you import GCRCatalogs,
            GCRCatalogs.set_root_dir_by_site('sitename')
       where sitename is one of ({})

       For anyone:
       If you want to set root dir in the current session to a value not
       associated with a site, use
            GCRCatalogs.set_root_dir('/path/to/your/root_dir')

       To also make that value the default in future sessions, use
            GCRCatalogs.set_root_dir('/path/to/your/root_dir',
                                     write_to_config=True)
       or, before starting Python, invoke the script user_config from the
       command line, e.g.
        $ python -m GCRCatalogs.user_config set root_dir /path/to/your/root_dir
    """

    def __init__(self, site_config_path=None, user_config_name=None):
        self._site_config_path = site_config_path
        self._user_config_manager = UserConfigManager(config_filename=user_config_name)
        self._default_root_dir = None
        self._custom_root_dir = None

        # Obtain site config content if available
        self._site_config = {}
        if self._site_config_path and os.path.isfile(self._site_config_path):
            self._site_config = load_yaml_local(self._site_config_path)

        # Try to set self._root_dir_from_config
        user_root_dir = self._user_config_manager.get(self._ROOT_DIR_KEY)
        if user_root_dir:
            self._default_root_dir = user_root_dir
            return

        # Try to set self._root_dir_from_site
        if self._site_config:
            site_name = get_site_name()
            if site_name:
                for k, v in self._site_config.items():
                    if k in site_name:
                        self._default_root_dir = v['root_dir']
                        break

    @property
    def root_dir(self):
        current_root_dir = self._custom_root_dir or self._default_root_dir
        if not current_root_dir:
            site_string = ' '.join(self.site_list)
            warnings.warn(self._NO_DEFAULT_ROOT_WARN.format(_DESC_SITE_ENV, site_string))

        return current_root_dir

    @root_dir.setter
    def root_dir(self, path):
        """
        If 'path' is acceptable, set root dir to it
        """
        # os.listdir will throw exception if path is ill-formed or doesn't exist
        try:
            os.listdir(path)
        except FileNotFoundError:
            warnings.warn("root_dir has been set to non-existent path '{}'".format(path))
        except NotADirectoryError:
            warnings.warn("root_dir has been set to a regular file '{}'; should be directory".format(path))
        except PermissionError:
            warnings.warn("root_dir has been set to '{}' but you have no permission to access it".format(path))
        except OSError as e:
            warnings.warn("root_dir has been set to '{}' but errors may occur when you try to access it: {}".format(path, e))
        self._custom_root_dir = path

    @property
    def site_list(self):
        return list(self._site_config)

    def set_root_dir_by_site(self, site):
        """
        If *site* is a recognized site, set root_dir to corresponding value
        """
        try:
            new_root_dir = self._site_config[site]
        except KeyError:
            site_string = ' '.join(self.site_list)
            warnings.warn(f"Unknown site '{site}'.\nAvailable sites are: {site_string}\nroot_dir is unchanged")
        else:
            self.root_dir = new_root_dir

    def persist_root_dir(self):
        """
        Write current session value of root_dir to user config.
        """
        self._user_config_manager[self._ROOT_DIR_KEY] = os.path.abspath(self.root_dir)

    def unpersist_root_dir(self):
        """
        Remove root_dir item from user config.  root_dir for the current
        session is unchanged, however.
        """
        self._user_config_manager.pop(self._ROOT_DIR_KEY, None)

    def reset_root_dir(self):
        self._custom_root_dir = None

    def resolve_root_dir(self, config_dict, config_name=None, record=None):
        """
        This function is a "resolver" function that is used to resolve
        config files.
        It should be supplied to `Config.set_resolvers`.

        *config_dict* is the input config dictionary and will be modified
        in-place, and also returned.

        *config_name* is the input catalog name (str).
        It has not specific use here other than to satisty the required call
        signature.

        *record* is an optional argument that is not used by
        `Config.set_resolvers`.
        It is used by `ConfigRegister.record_all_paths`.
        When *record* is set to a list, this function will append all paths it
        finds to *record*.
        This is useful to list all file paths in the configs.
        (Note that when *record* is set, *config_name* will be used to identify
         which config the corresponding path is found in.)
        """
        for k, v in config_dict.items():
            if k in self._PATH_LIKE_KEYS and is_string_like(v):
                orig_path = resolved_path = v
                if orig_path.startswith(self._ROOT_DIR_SIGNAL):
                    try:
                        resolved_path = os.path.join(self.root_dir,
                                                     orig_path[len(self._ROOT_DIR_SIGNAL):])
                    except TypeError:
                        pass
                    else:
                        config_dict[k] = resolved_path
                if record is not None:
                    record.append((config_name, orig_path, resolved_path))

            elif k in self._DICT_LIST_KEYS and isinstance(v, list):
                for c in v:
                    if isinstance(c, dict):
                        self.resolve_root_dir(c, config_name, record)

        return config_dict

    @property
    def has_valid_root_dir_in_site_config(self):
        root_dir = self.root_dir
        return bool(
            root_dir and
            os.path.abspath(root_dir) in [v['root_dir'] for v in self._site_config.values()] and
            os.path.isdir(root_dir) and
            os.access(root_dir, os.R_OK)
        )
