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

__all__ = ["get_root_dir", "set_root_dir", "reset_root_dir", "get_available_catalogs", "has_catalog", "load_catalog"]


_GITHUB_URL = "https://raw.githubusercontent.com/LSSTDESC/gcr-catalogs/master/GCRCatalogs"
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
        catalog_config["subclass_name"], __package__, BaseGenericCatalog
    )(**catalog_config)


# Classes

class RootDirManager:
    _ROOT_DIR_SIGNAL = "^/"
    _PATH_LIKE_KEYS = (
        "filename",
        "addon_filename",
        "base_dir",
        "root_dir",
        "catalog_root_dir",
        "header_file",
        "repo",
        "table_dir",
    )
    _DICT_LIST_KEYS = ("catalogs",)
    _DESC_SITE_ENV = "DESC_GCR_SITE"

    def __init__(self, site_config_path=None):
        self._site_config_path = site_config_path
        self._default_root_dir = None
        self._custom_root_dir = None
        self._site_info = self._get_site_info()

        if self._site_config_path:
            site_config = load_yaml_local(self._site_config_path)
            for k, v in site_config.items():
                if k in self._site_info:
                    self._default_root_dir = v
                    break

        if not self._default_root_dir:
            warnings.warn("Default root dir has not been set!")

    def _get_site_info(self):
        """
        Return a string which, when executing at a recognized site with
        well-known name, will include the name for that site
        """
        # First look for custom env variable
        v = os.getenv(self._DESC_SITE_ENV)
        if v:
            warnings.warn("Site determined from env variable {}".format(self._DESC_SITE_ENV))
            return v
        return socket.getfqdn()

    @property
    def root_dir(self):
        return self._custom_root_dir or self._default_root_dir

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

    def reset_root_dir(self):
        self._custom_root_dir = None

    def resolve_root_dir(self, config_dict, config_name=None):  # pylint: disable=unused-argument
        """
        input dictionary `config_dict` will be modified in-place and returned
        """
        for k, v in config_dict.items():
            if k in self._PATH_LIKE_KEYS and is_string_like(v) and v.startswith(self._ROOT_DIR_SIGNAL):
                try:
                    config_dict[k] = os.path.join(self.root_dir, v[len(self._ROOT_DIR_SIGNAL):])
                except TypeError:
                    warnings.warn("Root dir has not been set!")

            elif k in self._DICT_LIST_KEYS and isinstance(v, list):
                for c in v:
                    if isinstance(c, dict):
                        self.resolve_root_dir(c)

        return config_dict


class Config(Mapping):
    YAML_EXTENSIONS = (".yaml", ".yml")

    def __init__(self, config_path, config_dir="", resolvers=None):
        self.path = os.path.join(config_dir, config_path)
        self.basename = os.path.basename(self.path)
        self.rootname, self.ext = os.path.splitext(self.basename)
        self.name = self.rootname.lower()

        self._resolvers = None
        self._content = None
        self._resolved_content = None

        if resolvers:
            self.set_resolvers(*resolvers)

    def set_resolvers(self, *resolvers):
        if not all(map(callable, resolvers)):
            raise ValueError("`resolvers` should be callable.")
        self._resolvers = resolvers
        self.reset_resolved_content()

    @property
    def ignore(self):
        return self.rootname.startswith("_") or self.ext.lower() not in self.YAML_EXTENSIONS

    @property
    def content(self):
        if self._content is None:
            self._content = load_yaml_local(self.path)
        return self._content

    @property
    def resolved_content(self):
        if self._resolved_content is None:
            content = self.content_copy
            if self._resolvers:
                for resolver in self._resolvers:
                    content = resolver(content, self.name)
            if "subclass_name" not in content:
                raise ValueError(
                    "`subclass_name` is missing in the config of {}"
                    "and all of its references".format(self.name)
                )
            self._resolved_content = content
        return self._resolved_content

    def reset_resolved_content(self):
        self._resolved_content = None

    @property
    def content_copy(self):
        return copy.deepcopy(self.content)

    @property
    def resolved_content_copy(self):
        return copy.deepcopy(self.resolved_content)

    def __getitem__(self, key):
        return self.content[key]

    def __iter__(self):
        return iter(self.content)

    def __len__(self):
        return len(self.content)

    @property
    def is_default(self):
        return self.get("include_in_default_catalog_list")

    @property
    def is_pseudo(self):
        return self.get("is_pseudo_entry")

    @property
    def is_alias(self):
        return self.get("alias")

    @staticmethod
    def _has_reference_keys(d):
        return d.get("alias") or d.get("based_on")

    @property
    def has_reference(self):
        return self._has_reference_keys(self)

    def load_catalog(self, config_overwrite=None):
        self.online_alias_check()
        if config_overwrite:
            if self._has_reference_keys(config_overwrite):
                raise ValueError("`config_overwrite` cannot specify `alias` or `based_on`!")
        return load_catalog_from_config_dict(dict(self.resolved_content, **config_overwrite))

    def online_alias_check(self):
        if not self.is_alias:
            return

        url = "/".join((_GITHUB_URL, _CONFIG_DIRNAME, self.basename))
        try:
            online_config = load_yaml(url)
        except (requests.RequestException, yaml.error.YAMLError):
            return

        if self["alias"] != online_config.get("alias"):
            warnings.warn(
                "`{}` is currently an alias of `{}`."
                "Please be advised that it will soon change to point to an updated version `{}`."
                "The updated version is already available in the master branch.".format(
                    self.rootname, self["alias"], online_config.get("alias"),
                )
            )


class ConfigManager(Mapping):

    YAML_EXTENSIONS = Config.YAML_EXTENSIONS

    def __init__(self, config_dir):
        self._config_dir = config_dir
        self._configs = dict()
        for config_file in sorted(os.listdir(self._config_dir)):
            config = Config(config_file, self._config_dir)
            if not config.ignore:
                self._configs[config.name] = config

    def normalize_name(self, name):
        name = str(name).lower()
        for extension in self.YAML_EXTENSIONS:
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

    def resolve_reference(self, config_dict, config_name=None, past_refs=None):
        if past_refs is None and config_name is not None:
            past_refs = [config_name]

        for key in ("alias", "based_on"):
            if config_dict.get(key):
                base_name = self.normalize_name(config_dict[key])
                base_config_dict = self[base_name].content_copy

                if past_refs is None:
                    past_refs = [base_name]
                elif base_name in past_refs:
                    raise RecursionError("Recursive reference (alias or based_on) of `{}`".format(base_name))
                else:
                    past_refs.append(base_name)

                if key == "based_on":
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
        include_pseudo=False,
        include_pseudo_only=False,
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
                get_content = lambda config: config.resolved_content_copy  # noqa: E731
            else:
                get_content = lambda config: config.content_copy  # noqa: E731
        else:
            return_type = dict
            if resolve_content:
                get_content = lambda config: (config.rootname, config.resolved_content_copy)  # noqa: E731
            else:
                get_content = lambda config: (config.rootname, config.content_copy)  # noqa: E731

        conditions = list()
        if include_default_only:
            conditions.append(lambda config: config.is_default)
        if include_pseudo_only:
            conditions.append(lambda config: config.is_pseudo)
        elif not include_pseudo:
            conditions.append(lambda config: not config.is_pseudo)
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

        return return_type((get_content(v) for v in self.values() if check_conditions(v)))

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
        configs = self.get_configs(content_only=True, resolve_content=True, include_pseudo=False)
        return list(set((v["subclass_name"] for v in configs)))


class ConfigRegister(RootDirManager, ConfigManager):
    def __init__(self, config_dir, site_config_path=None):
        ConfigManager.__init__(self, config_dir)
        RootDirManager.__init__(self, site_config_path)
        for v in self.values():
            v.set_resolvers(self.resolve_reference, self.resolve_root_dir)

    @property
    def root_dir(self):
        return super().root_dir

    @root_dir.setter
    def root_dir(self, path):
        for v in self.values():
            v.reset_resolved_content()
        RootDirManager.root_dir.__set__(self, path)  # pylint: disable=no-member


# module-level functions that access/manipulate _config_register

def get_root_dir():
    """
    Returns current root_dir.
    """
    return _config_register.root_dir


def set_root_dir(path):
    """
    Sets runtime root_dir to *path*.
    """
    _config_register.root_dir = path


def reset_root_dir():
    """
    Resets runtime root_dir to its default value.
    """
    _config_register.reset_root_dir()


def get_available_catalogs(include_default_only=True, names_only=False, **kwargs):
    """
    Returns all available catalogs and their corresponding config files
    as a dictionary (when *names_only* set to False),
    or returns available catalog names as a list (when *names_only* set to True).

    If *include_default_only* is set to False, the returned list/dict will
    include catalogs that are not in the default listing.
    """
    return _config_register.get_configs(
        names_only=names_only, include_default_only=include_default_only, **kwargs
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
    if raw_config:
        return _config_register[catalog_name].content_copy
    return _config_register[catalog_name].resolved_content_copy


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
    _config_register[catalog_name].load_catalog(config_overwrite)


_config_register = ConfigRegister(_CONFIG_DIRPATH, _SITE_CONFIG_PATH)
