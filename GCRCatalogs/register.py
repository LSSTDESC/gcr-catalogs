import os
import warnings
import yaml             # now needed only for error reporting
import requests         # now needed only for error reporting
from collections import namedtuple
from .root_dir_manager import RootDirManager
from .catalog_helpers import load_yaml_local, load_yaml
from .base_config import BaseConfig, BaseConfigManager
from .dr_register import DR_AVAILABLE

__all__ = [
    "get_root_dir", "set_root_dir", "remove_root_dir_default",
    "reset_root_dir", "get_available_catalogs", "get_reader_list",
    "get_catalog_config", "has_catalog", "load_catalog", "retrieve_paths",
    "get_site_list", "set_root_dir_by_site", "get_available_catalog_names",
    "get_public_catalog_names", "ConfigSource", "DR_AVAILABLE"]

_GITHUB_REPO = "LSSTDESC/gcr-catalogs"
_GITHUB_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/master/GCRCatalogs"
_HERE = os.path.dirname(__file__)
_CONFIG_DIRNAME = "catalog_configs"
_CONFIG_DIRPATH = os.path.join(_HERE, _CONFIG_DIRNAME)
_SITE_CONFIG_PATH = os.path.join(_HERE, "site_config", "site_rootdir.yaml")
_CONFIG_SOURCE_ENV = "GCR_CONFIG_SOURCE"
_DR_SCHEMA_ENV = "GCR_DR_SCHEMA"
_DR_SCHEMA_DEFAULT = "lsst_desc_production"


# Classes
class Config(BaseConfig):

    def __init__(self, config_path, config_dir="", resolvers=None):
        self.path = os.path.join(config_dir, config_path)
        self.basename = os.path.basename(self.path)
        rootname, self.ext = os.path.splitext(self.basename)
        name = rootname.lower()
        super().__init__(name=name, rootname=rootname)

        if resolvers:
            self.set_resolvers(*resolvers)

    @property
    def ignore(self):
        return self.rootname.startswith("_") or self.ext.lower() not in self.YAML_EXTENSIONS

    @property
    def _content(self):
        if self._content_ is None:
            self._content_ = load_yaml_local(self.path)
        return self._content_

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


class ConfigManager(BaseConfigManager):

    def __init__(self, config_dir):
        super().__init__()
        self._config_dir = config_dir
        # self._configs = dict()
        for config_file in sorted(os.listdir(self._config_dir)):
            config = Config(config_file, self._config_dir)
            if not config.ignore:
                self._configs[config.name] = config


class ConfigRegister(RootDirManager, ConfigManager):
    def __init__(self, config_dir, site_config_path=None,
                 user_config_name=None):
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


# module-level functions that access/manipulate ConfigSource.config_source
def check_for_reg():
    if not ConfigSource.config_source:
        if not DR_AVAILABLE:
            ConfigSource.set_config_source()
            return
        else:
            msg = f'''
Set env variable {_CONFIG_SOURCE_ENV} to acceptable value
("dataregistry" or "files") or call ConfigSource.set_config_source'''
            # See if user has set environment variable to select source
            source = os.getenv(_CONFIG_SOURCE_ENV, None)
            if not source:
                raise RuntimeError("Registry source has not been established." + msg)
            if source == "dataregistry":
                dr_schema = os.getenv(_DR_SCHEMA_ENV, _DR_SCHEMA_DEFAULT)
                ConfigSource.set_config_source(True, dr_schema=dr_schema)
                return
            elif source == "files":
                ConfigSource.set_config_source(False)
                return
            else:
                raise RuntimeError(
                    f"Unknown value {source} for GCR_CONFIG_SOURCE." + msg)


def get_root_dir():
    """
    Returns current root_dir.
    """
    check_for_reg()
    return ConfigSource.config_source.root_dir


def set_root_dir(path, write_to_config=False):
    """
    Sets runtime root_dir to *path*.
    """
    check_for_reg()
    ConfigSource.config_source.root_dir = path

    if write_to_config:
        ConfigSource.config_source.persist_root_dir()


def set_root_dir_by_site(site):
    """
    Sets runtime root_dir to path corresponding to *site*.
    """
    check_for_reg()
    ConfigSource.config_source.set_root_dir_by_site(site)


def remove_root_dir_default():
    """
    Revert to state of no user default root dir

    """
    check_for_reg()
    ConfigSource.config_source.unpersist_root_dir()


def get_site_list():
    """
    Return list of recognized sites
    """
    check_for_reg()
    return ConfigSource.config_source.site_list


def reset_root_dir():
    """
    Resets runtime root_dir to its default value.
    """
    check_for_reg()
    ConfigSource.config_source.reset_root_dir()


def get_available_catalogs(
    include_default_only=True,
    names_only=False,
    name_startswith=None,
    name_contains=None,
    **kwargs
):
    """
    Returns a dictionary of all available catalogs and their corresponding
    configs.

    Parameters
    ----------
    include_default_only: bool, optional (default: True)
        When set to False, returned list will include catalogs that are not
        in the default listing
        (i.e., those may not be suitable for general comsumption)
    names_only: bool, optional (default: False)
        When set to True, ruturns just a list of catalog names.
    name_startswith: str, optional (default: None)
        If set, only return catalogs whose name starts with *name_startswith*
    name_contains: str, optional (default: None)
        If set, only return catalogs whose name contains with *name_contains*
    """
    check_for_reg()
    if not kwargs.get("include_public_release_only") and not ConfigSource.config_source.has_valid_root_dir_in_site_config:
        warnings.warn("""It appears that you do not have access to the default
     root dir at a recognized DESC site or you are using a customized root dir.
        As such, the returned catalogs may not all be available to you.
        Use get_public_catalog_names to see a list of catalogs from public
        releases only.
        If you are a DESC member and believe you are getting this warning by
        mistake, please contact DESC help.""")
    kwargs.setdefault("resolve_content", (not names_only))
    return ConfigSource.config_source.get_configs(
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
        When set to False, returned list will include catalogs that are not
        in the default listing
        (i.e., those which may not be suitable for general consumption)
    name_startswith: str, optional (default: None)
        If set, only return catalogs whose name starts with *name_startswith*
    name_contains: str, optional (default: None)
        If set, only return catalogs whose name contains *name_contains*
    """
    check_for_reg()
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
    Returns a list of names of all available catalog satisfying any constraints
    specified in parameters.

    Parameters
    ----------
    include_default_only: bool, optional (default: True)
        When set to False, returned list will include catalogs that are not
        in the default listing
        (i.e., those which may not be suitable for general consumption)
    name_startswith: str, optional (default: None)
        If set, only return catalogs whose name starts with *name_startswith*
    name_contains: str, optional (default: None)
        If set, only return catalogs whose name contains *name_contains*
    public_release_name: str, optional (default: None)
        If set, only return catalogs that are part of *public_release_name*
    """
    check_for_reg()
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
    check_for_reg()
    return ConfigSource.config_source.reader_list


def get_catalog_config(catalog_name, raw_config=False):
    """
    Returns the config dict of *catalog_name*.
    If *raw_config* set to `True`, do not resolve references (alias, based_on)
    """
    check_for_reg()
    config = ConfigSource.config_source[catalog_name]  # pylint: disable=unsubscriptable-object
    return config.content if raw_config else config.resolved_content


def has_catalog(catalog_name, include_pseudo=False):
    """
    Checks if *catalog_name* exists
    """
    check_for_reg()
    lower_name = catalog_name.lower()
    return lower_name in ConfigSource.config_source._configs and (
        include_pseudo or not ConfigSource.config_source._configs[lower_name].is_pseudo  # pylint: disable=unsubscriptable-object
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
    catalog : instance of a subclass of BaseGenericCatalog
    """
    check_for_reg()
    return ConfigSource.config_source[catalog_name].load_catalog(config_overwrite)  # pylint: disable=unsubscriptable-object


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
    check_for_reg()
    return ConfigSource.config_source.retrieve_paths(
        name_startswith=name_startswith, name_contains=name_contains, **kwargs
    )


_dr_params = namedtuple("Dr_params", ["dr_root", "dr_schema", "dr_site"])


class ConfigSource():
    config_source = None
    file_source = None
    dr_sources = []

    @staticmethod
    def set_config_source(dr=False, dr_root=None, dr_schema=_DR_SCHEMA_DEFAULT,
                          dr_site=None):
        """
        Set up (or recover set up for) the specified source of config
        information: either from the yaml files in the gcr-catalogs repo
        or from the dataregistry.

        Parameters
        ----------
        dr        boolean  True if dataregistry is the source; False otherwise

        The remaining parameters only apply to the dataregistry source

        dr_root   str   Top of file hierarchy.  If None, the dataregistry
                        default will be used
        dr_schema str   Schema to use; typically "production" or the
                        dataregistry default
        dr_site   str   If None, the usual protocol for dataregistry will
                        be used to find the value

        If the user returns to the dataregistry source after using the file
        source, values for dr_root, dr_schema and dr_site will be ignored.
        The original values will still be used.
        """
        if dr and DR_AVAILABLE:
            from .dr_register import DrConfigRegister

            dr_params = _dr_params(dr_root, dr_schema, dr_site)
            for elt in ConfigSource.dr_sources:
                if elt[1] == dr_params:
                    ConfigSource.config_source = elt[0]
                    return elt[0]
            # No existing config source with these parameters so make
            # a new one
            reg = DrConfigRegister(_SITE_CONFIG_PATH,
                                   dr_root=dr_root,
                                   dr_schema=dr_schema,
                                   dr_site=dr_site)
            ConfigSource.dr_sources.append((reg, dr_params))
            ConfigSource.config_source = reg
            return reg
        else:
            if not ConfigSource.file_source:
                ConfigSource.file_source = ConfigRegister(_CONFIG_DIRPATH,
                                                          _SITE_CONFIG_PATH)
            reg = ConfigSource.file_source
            ConfigSource.config_source = reg
            return reg

    @staticmethod
    def get_config_source():
        return ConfigSource.config_source

    @staticmethod
    def resume_config_source(config_source):
        if isinstance(config_source, ConfigRegister):
            ConfigSource.config_source = config_source
            return config_source

        if DR_AVAILABLE:
            from .dr_register import DrConfigRegister

            if isinstance(config_source, DrConfigRegister):
                for elt in ConfigSource.dr_sources:
                    if config_source == elt[0]:
                        ConfigSource.config_source = config_source
                        return config_source
                else:
                    raise ValueError("Unknown config source")
        else:
            raise ValueError("Improper argument to ConfigSource.resume_config_source")
