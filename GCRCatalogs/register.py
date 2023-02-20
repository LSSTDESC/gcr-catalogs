import os
import importlib
import warnings
import copy
from collections.abc import Mapping
import yaml
import requests
import socket
from GCR import BaseGenericCatalog
from .utils import is_string_like
from .user_config_mgr import UserConfigManager

__all__ = [
    "get_root_dir", "set_root_dir", "remove_root_dir_default", "reset_root_dir", "get_available_catalogs",
    "get_reader_list", "get_catalog_config", "has_catalog", "load_catalog", "retrieve_paths", "get_site_list", "set_root_dir_by_site", "get_available_catalog_names", "get_public_catalog_names"]

_GITHUB_REPO = "LSSTDESC/gcr-catalogs"
_GITHUB_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/master/GCRCatalogs"
_GITHUB_ISSUE_URL = f"https://github.com/{_GITHUB_REPO}/issues"
_HERE = os.path.dirname(__file__)
_CONFIG_DIRNAME = "catalog_configs"
_CONFIG_DIRPATH = os.path.join(_HERE, _CONFIG_DIRNAME)
_SITE_CONFIG_PATH = os.path.join(_HERE, "site_config", "site_rootdir.yaml")


# yaml helper functions

def load_yaml_local(yaml_file):
    """
    Loads a yaml file on disk at path *yaml_file*.
    Returns a dictionary.
    """
    with open(yaml_file) as f:
        return yaml.safe_load(f)


def load_yaml(yaml_file):
    """
    Loads a yaml file either on disk at path *yaml_file*,
    or from the URL *yaml_file*.
    Returns a dictionary.
    """
    try:
        r = requests.get(yaml_file, stream=True)
    except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired):
        config = load_yaml_local(yaml_file)
    else:
        if r.status_code == 404:
            raise requests.RequestException("404 Not Found!")
        r.raw.decode_content = True
        config = yaml.safe_load(r.raw)
    return config


# catalog loading helper functions

def import_subclass(subclass_path, package=None, required_base_class=None):
    """
    Imports and returns a subclass.
    *subclass_path* must be in the form of module.subclass.
    """
    module, _, subclass_name = subclass_path.rpartition(".")
    if package and not module.startswith("."):
        module = "." + module
    subclass = getattr(importlib.import_module(module, package), subclass_name)
    if required_base_class and not issubclass(subclass, required_base_class):
        raise ValueError("Provided class is not a subclass of *required_base_class*")
    return subclass


def load_catalog_from_config_dict(catalog_config):
    """
    Loads and returns the catalog specified in *catalog_config*.
    """
    return import_subclass(
        catalog_config[Config.READER_KEY], __package__, BaseGenericCatalog
    )(**catalog_config)


# Classes

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
    _DESC_SITE_ENV = "DESC_GCR_SITE"
    _NO_DEFAULT_ROOT_WARN = """
       Default root dir has not been set; catalogs may not be found.

       For DESC users:
       You can specify the site as an environment variable before you import GCRCatalogs,
            $ export {}='sitename'
       or, from within Python and after you import GCRCatalogs,
            GCRCatalogs.set_root_dir_by_site('sitename')
       where sitename is one of ({})

       For anyone:
       If you want to set root dir in the current session to a value not associated with
       a site, use
            GCRCatalogs.set_root_dir('/path/to/your/root_dir')

       To also make that value the default in future sessions, use
            GCRCatalogs.set_root_dir('/path/to/your/root_dir', write_to_config=True)
       or, before starting Python, invoke the script user_config from the command line, e.g.
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
            site_info = self._get_site_info()
            if site_info:
                for k, v in self._site_config.items():
                    if k in site_info:
                        self._default_root_dir = v
                        break

    def _get_site_info(self):
        """
        Return a string which, when executing at a recognized site with
        well-known name, will include the name for that site
        """
        site_from_env = os.getenv(self._DESC_SITE_ENV, "")
        if site_from_env:
            return site_from_env

        if  os.getenv("NERSC_HOST", ""):
            site_from_node = 'nersc'
        else:
            site_from_node = None
        return site_from_node

    @property
    def root_dir(self):
        current_root_dir = self._custom_root_dir or self._default_root_dir
        if not current_root_dir:
            site_string = ' '.join(self.site_list)
            warnings.warn(self._NO_DEFAULT_ROOT_WARN.format(self._DESC_SITE_ENV, site_string))

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
        This function is a "resolver" function that is used to resolve config files.
        It should be supplied to `Config.set_resolvers`.

        *config_dict* is the input config dictionary and will be modified in-place, and also returned.

        *config_name* is the input catalog name (str).
        It has not specific use here other than to satisty the required call signature.

        *record* is an optional argument that is not used by `Config.set_resolvers`.
        It is used by `ConfigRegister.record_all_paths`.
        When *record* is set to a list, this function will append all paths it finds to *record*.
        This is useful to list all file paths in the configs.
        (Note that when *record* is set, *config_name* will be used to identify
         which config the corresponding path is found in.)
        """
        for k, v in config_dict.items():
            if k in self._PATH_LIKE_KEYS and is_string_like(v):
                orig_path = resolved_path = v
                if orig_path.startswith(self._ROOT_DIR_SIGNAL):
                    try:
                        resolved_path = os.path.join(self.root_dir, orig_path[len(self._ROOT_DIR_SIGNAL):])
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
            os.path.abspath(root_dir) in self._site_config.values() and
            os.path.isdir(root_dir) and
            os.access(root_dir, os.R_OK)
        )


class Config(Mapping):
    YAML_EXTENSIONS = (".yaml", ".yml")
    ALIAS_KEY = "alias"
    REFERENCE_KEYS = (ALIAS_KEY, "based_on")
    PSEUDO_KEY = "is_pseudo_entry"
    DEFAULT_LISTING_KEY = "include_in_default_catalog_list"
    READER_KEY = "subclass_name"
    DEPRECATED_KEY = "deprecated"
    ADDON_KEY = "addon_for"
    PUBLIC_RELEASE_KEY = "public_release"

    def __init__(self, config_path, config_dir="", resolvers=None):
        self.path = os.path.join(config_dir, config_path)
        self.basename = os.path.basename(self.path)
        self.rootname, self.ext = os.path.splitext(self.basename)
        self.name = self.rootname.lower()

        self._resolvers = None
        self._content_ = None
        self._resolved_content_ = None

        if resolvers:
            self.set_resolvers(*resolvers)

    def set_resolvers(self, *resolvers):
        """
        Each resolver will be called with two arguments: `resolver(config_dict, config_name)`
        and it should return a config dictionary
        """
        if not all(map(callable, resolvers)):
            raise ValueError("`resolvers` should be callable.")
        self._resolvers = resolvers
        self.reset_resolved_content()

    @property
    def ignore(self):
        return self.rootname.startswith("_") or self.ext.lower() not in self.YAML_EXTENSIONS

    @property
    def _content(self):
        if self._content_ is None:
            self._content_ = load_yaml_local(self.path)
        return self._content_

    @property
    def _resolved_content(self):
        if self._resolved_content_ is None:
            content = self.content
            if self._resolvers:
                for resolver in self._resolvers:
                    content = resolver(content, self.name)
            if any(map(content.get, self.REFERENCE_KEYS)):
                raise ValueError("Fail to resolve references for config `{}`!".format(self.rootname))
            elif not (content.get(self.READER_KEY) or self.is_pseudo):
                raise ValueError("`{}` is missing in config `{}` and its references!".format(self.READER_KEY, self.rootname))
            self._resolved_content_ = content
        return self._resolved_content_

    def reset_resolved_content(self):
        self._resolved_content_ = None

    @property
    def content(self):
        return copy.deepcopy(self._content)

    @property
    def resolved_content(self):
        return copy.deepcopy(self._resolved_content)

    def __getitem__(self, key):
        return self._content[key]

    def __iter__(self):
        return iter(self._content)

    def __len__(self):
        return len(self._content)

    @property
    def is_valid(self):
        return self.get(self.READER_KEY) or self.is_pseudo or self.has_reference

    @property
    def is_default(self):
        return self.get(self.DEFAULT_LISTING_KEY) and not self.is_deprecated and not self.is_pseudo

    @property
    def is_pseudo(self):
        return self.get(self.PSEUDO_KEY)

    @property
    def is_alias(self):
        return self.get(self.ALIAS_KEY)

    @property
    def is_deprecated(self):
        return self.get(self.DEPRECATED_KEY)

    @property
    def is_addon(self):
        return self.get(self.ADDON_KEY)

    @property
    def is_public_release(self):
        return self.get(self.PUBLIC_RELEASE_KEY)

    @property
    def has_reference(self):
        return any(map(self.get, self.REFERENCE_KEYS))

    def load_catalog(self, config_overwrite=None):
        if self.is_pseudo:
            raise RuntimeError(
                "This is a pseudo entry that does not have an associated reader and cannot be loaded."
                f"Use GCRCatalogs.get_catalog_config({self.rootname}) to see the content of this config file."
            )
        if self.is_deprecated:
            deprecation_msg = self[self.DEPRECATED_KEY]
            if is_string_like(deprecation_msg):
                deprecation_msg = deprecation_msg.strip() + "\n"
            else:
                deprecation_msg = ""
            warnings.warn(
                f"`{self.rootname}` has been deprecated and may be removed in the future.\n{deprecation_msg}"
                f"If your analysis requires this specific catalog, please open an issue at {_GITHUB_ISSUE_URL}",
            )
        self.online_alias_check()
        if config_overwrite:
            if any(map(config_overwrite.get, self.REFERENCE_KEYS)):
                raise ValueError("`config_overwrite` cannot specify " + " or ".join(self.REFERENCE_KEYS))
            config_dict = dict(self._resolved_content, **config_overwrite)
        else:
            config_dict = self._resolved_content
        return load_catalog_from_config_dict(config_dict)

    def online_alias_check(self):
        if not self.is_alias:
            return

        url = "/".join((_GITHUB_URL, _CONFIG_DIRNAME, self.basename))
        try:
            online_config = load_yaml(url)
        except (requests.RequestException, yaml.error.YAMLError):
            return

        if self[self.ALIAS_KEY] != online_config.get(self.ALIAS_KEY):
            warnings.warn(
                "`{}` is currently an alias of `{}`."
                "Please be advised that it will soon change to point to an updated version `{}`."
                "The updated version is already available in the master branch.".format(
                    self.rootname, self[self.ALIAS_KEY], online_config.get(self.ALIAS_KEY),
                )
            )


class ConfigManager(Mapping):

    def __init__(self, config_dir):
        self._config_dir = config_dir
        self._configs = dict()
        for config_file in sorted(os.listdir(self._config_dir)):
            config = Config(config_file, self._config_dir)
            if not config.ignore:
                self._configs[config.name] = config

    def normalize_name(self, name):
        name = str(name).lower()
        for extension in Config.YAML_EXTENSIONS:
            if name.endswith(extension):
                return name[:-len(extension)]
        return name

    def __getitem__(self, key):
        try:
            return self._configs[self.normalize_name(key)]
        except KeyError:
            raise KeyError("Catalog `{}` does not exist.".format(key))

    def __iter__(self):
        return iter(self._configs)

    def __len__(self):
        return len(self._configs)

    @property
    def configs(self):
        return self.values()

    def resolve_reference(self, config_dict, config_name=None, past_refs=None):
        """
        This function is a "resolver" function that is used to resolve config files.
        It should be supplied to `Config.set_resolvers`.

        *config_dict* is the input config dictionary and may be modified in-place, and will be returned.

        *config_name* is the input catalog name (str).
        It is used to detect recursive reference, and also to satisty the required call signature.

        *past_refs* is an optional argument for this function's internal use to detect recursive reference,
        """
        if past_refs is None and config_name is not None:
            past_refs = [config_name]

        for key in Config.REFERENCE_KEYS:
            if config_dict.get(key):
                base_name = self.normalize_name(config_dict[key])
                base_config_dict = self[base_name].content

                if past_refs is None:
                    past_refs = [base_name]
                elif base_name in past_refs:
                    raise RecursionError("Recursive reference to `{}` in config file `{}`".format(base_name, config_name))
                else:
                    past_refs.append(base_name)

                if key != Config.ALIAS_KEY:
                    del config_dict[key]
                    base_config_dict.update(config_dict)

                return self.resolve_reference(base_config_dict, past_refs=past_refs)

        return config_dict

    def get_configs(
        self,
        names_only=False,
        content_only=False,
        resolve_content=False,
        include_default_only=False,
        include_addons=False,
        include_deprecated=False,
        include_pseudo=False,
        include_pseudo_only=False,
        include_public_release=False,
        include_public_release_only=False,
        name_startswith=None,
        name_contains=None,
        additional_conditions=None,
    ):
        if names_only and content_only:
            raise ValueError(
                "Options `names_only` and `content_only` cannot both be set to True."
            )
        elif names_only:
            return_type = list
            get_content = lambda config: config.rootname  # noqa: E731
            if resolve_content:
                raise ValueError(
                    "Options `names_only` and `resolve_content` cannot both be set to True."
                )
        elif content_only:
            return_type = list
            if resolve_content:
                get_content = lambda config: config.resolved_content  # noqa: E731
            else:
                get_content = lambda config: config.content  # noqa: E731
        else:
            return_type = dict
            if resolve_content:
                get_content = lambda config: (config.rootname, config.resolved_content)  # noqa: E731
            else:
                get_content = lambda config: (config.rootname, config.content)  # noqa: E731

        conditions = list()
        if include_default_only:
            conditions.append(lambda config: config.is_default)
        if not include_addons:
            conditions.append(lambda config: not config.is_addon)
        if not include_deprecated:
            conditions.append(lambda config: not config.is_deprecated)
        if include_pseudo_only:
            conditions.append(lambda config: config.is_pseudo)
        elif not include_pseudo:
            conditions.append(lambda config: not config.is_pseudo)
        if include_public_release_only is True:
            conditions.append(lambda config: config.is_public_release)
        elif include_public_release_only:
            conditions.append(lambda config: config.is_public_release and include_public_release_only in config.is_public_release)
        elif not include_public_release:
            conditions.append(lambda config: not config.is_public_release)
        if name_startswith:
            name_startswith_lower = str(name_startswith).lower()
            conditions.append(lambda config: config.name.startswith(name_startswith_lower))
        if name_contains:
            name_contains_lower = str(name_contains).lower()
            conditions.append(lambda config: name_contains_lower in config.name)
        if additional_conditions:
            conditions.extend(additional_conditions)

        def check_conditions(config):
            return all((condition(config) for condition in conditions))

        return return_type((get_content(v) for v in self.configs if check_conditions(v)))

    @property
    def catalog_configs(self):
        return self.get_configs(resolve_content=True, include_pseudo=False)

    @property
    def default_catalog_configs(self):
        return self.get_configs(resolve_content=True, include_default_only=True, include_pseudo=False)

    @property
    def catalog_list(self):
        return self.get_configs(names_only=True, include_pseudo=False)

    @property
    def default_catalog_list(self):
        return self.get_configs(names_only=True, include_default_only=True, include_pseudo=False)

    @property
    def reader_list(self):
        configs = self.get_configs(content_only=True, resolve_content=True, include_addons=True,
                                   include_deprecated=True, include_pseudo=False)
        return list(set((v[Config.READER_KEY] for v in configs)))


class ConfigRegister(RootDirManager, ConfigManager):
    def __init__(self, config_dir, site_config_path=None, user_config_name=None):
        ConfigManager.__init__(self, config_dir)
        RootDirManager.__init__(self, site_config_path, user_config_name)
        for config in self.configs:
            config.set_resolvers(self.resolve_reference, self.resolve_root_dir)

    @property
    def root_dir(self):
        return super().root_dir

    @root_dir.setter
    def root_dir(self, path):
        for config in self.configs:
            config.reset_resolved_content()
        RootDirManager.root_dir.__set__(self, path)  # pylint: disable=no-member

    def retrieve_paths(self, **kwargs):
        kwargs["names_only"] = False
        kwargs["content_only"] = False
        kwargs["resolve_content"] = False
        record = list()
        for config_name, config_dict in self.get_configs(**kwargs).items():
            self.resolve_root_dir(config_dict, config_name, record)
        return record


# module-level functions that access/manipulate _config_register

def get_root_dir():
    """
    Returns current root_dir.
    """
    return _config_register.root_dir


def set_root_dir(path, write_to_config=False):
    """
    Sets runtime root_dir to *path*.
    """
    _config_register.root_dir = path

    if write_to_config:
        _config_register.persist_root_dir()


def set_root_dir_by_site(site):
    """
    Sets runtime root_dir to path corresponding to *site*.
    """
    _config_register.set_root_dir_by_site(site)


def remove_root_dir_default():
    """
    Revert to state of no user default root dir

    """
    _config_register.unpersist_root_dir()


def get_site_list():
    """
    Return list of recognized sites
    """
    return _config_register.site_list


def reset_root_dir():
    """
    Resets runtime root_dir to its default value.
    """
    _config_register.reset_root_dir()


def get_available_catalogs(
    include_default_only=True,
    names_only=False,
    name_startswith=None,
    name_contains=None,
    **kwargs
):
    """
    Returns a dictionary of all available catalogs and their corresponding configs.

    Parameters
    ----------
    include_default_only: bool, optional (default: True)
        When set to False, returned list will include catalogs that are not in the default listing
        (i.e., those may not be suitable for general comsumption)
    names_only: bool, optional (default: False)
        When set to True, ruturns just a list of catalog names.
    name_startswith: str, optional (default: None)
        If set, only return catalogs whose name starts with *name_startswith*
    name_contains: str, optional (default: None)
        If set, only return catalogs whose name contains with *name_contains*
    """
    if not kwargs.get("include_public_release_only") and not _config_register.has_valid_root_dir_in_site_config:
        warnings.warn("""It appears that you do not have access to the default root dir at a recognized DESC site, or you are using a customized root dir.
As such, the returned catalogs may not all be available to you.
Use get_public_catalog_names to see a list of catalogs from public releases only.
If you are a DESC member and believe you are getting this warning by mistake, please contact DESC help.""")
    kwargs.setdefault("resolve_content", (not names_only))
    return _config_register.get_configs(
        names_only=names_only,
        include_default_only=include_default_only,
        name_startswith=name_startswith,
        name_contains=name_contains,
        **kwargs
    )


def get_available_catalog_names(
    include_default_only=True,
    name_startswith=None,
    name_contains=None,
    **kwargs
):
    """
    Returns a list of all available catalog names.

    Parameters
    ----------
    include_default_only: bool, optional (default: True)
        When set to False, returned list will include catalogs that are not in the default listing
        (i.e., those which may not be suitable for general consumption)
    name_startswith: str, optional (default: None)
        If set, only return catalogs whose name starts with *name_startswith*
    name_contains: str, optional (default: None)
        If set, only return catalogs whose name contains *name_contains*
    """
    kwargs["names_only"] = True
    return get_available_catalogs(
        include_default_only=include_default_only,
        name_startswith=name_startswith,
        name_contains=name_contains,
        **kwargs
    )


def get_public_catalog_names(
    include_default_only=True,
    name_startswith=None,
    name_contains=None,
    public_release_name=None,
    **kwargs
):
    """
    Returns a list of names of all available catalog satisfying any constraints specified in parameters.

    Parameters
    ----------
    include_default_only: bool, optional (default: True)
        When set to False, returned list will include catalogs that are not in the default listing
        (i.e., those which may not be suitable for general consumption)
    name_startswith: str, optional (default: None)
        If set, only return catalogs whose name starts with *name_startswith*
    name_contains: str, optional (default: None)
        If set, only return catalogs whose name contains *name_contains*
    public_release_name: str, optional (default: None)
        If set, only return catalogs that are part of *public_release_name*
    """
    kwargs["names_only"] = True
    kwargs["include_public_release_only"] = public_release_name or True
    return get_available_catalogs(
        include_default_only=include_default_only,
        name_startswith=name_startswith,
        name_contains=name_contains,
        **kwargs
    )


def get_reader_list():
    """
    Returns a list of all readers
    """
    return _config_register.reader_list


def get_catalog_config(catalog_name, raw_config=False):
    """
    Returns the config dict of *catalog_name*.
    If *raw_config* set to `True`, do not resolve references (alias, based_on)
    """
    config = _config_register[catalog_name]
    return config.content if raw_config else config.resolved_content


def has_catalog(catalog_name, include_pseudo=False):
    """
    Checks if *catalog_name* exists
    """
    return catalog_name in _config_register and (
        include_pseudo or not _config_register[catalog_name].is_pseudo
    )


def load_catalog(catalog_name, config_overwrite=None):
    """
    Load a catalog as specified in the yaml file named *catalog_name*,
    with any *config_overwrite* options overwrite the default.

    Parameters
    ----------
    catalog_name : str
        name of the catalog
    config_overwrite : dict, optional
        a dictionary of config options to overwrite

    Return
    ------
    catalog : instance of a subclass of BaseGalaxyCatalog
    """
    return _config_register[catalog_name].load_catalog(config_overwrite)


def retrieve_paths(name_startswith=None, name_contains=None, **kwargs):
    """
    Retrieve all paths that are specificed in the configs files.

    Parameters
    ----------
    name_startswith: str, optional (default: None)
        If set, only return catalogs whose name starts with *name_startswith*
    name_contains: str, optional (default: None)
        If set, only return catalogs whose name contains with *name_contains*

    Return
    ------
    A list of tuples.
    The format would be [(catalog_name, original_path, resolved_path), ...]
    """
    return _config_register.retrieve_paths(name_startswith=name_startswith, name_contains=name_contains, **kwargs)


_config_register = ConfigRegister(_CONFIG_DIRPATH, _SITE_CONFIG_PATH)
