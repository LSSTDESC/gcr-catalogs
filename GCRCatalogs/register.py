import os
import importlib
import warnings
import yaml
import requests
from GCR import BaseGenericCatalog


__all__ = ['available_catalogs', 'get_available_catalogs', 'load_catalog']

_CONFIG_DIRNAME = 'catalog_configs'
_GITHUB_URL = 'https://raw.githubusercontent.com/LSSTDESC/gcr-catalogs/master/GCRCatalogs'


def load_yaml(yaml_file):
    """
    Load *yaml_file*. Ruturn a dictionary.
    """
    try:
        r = requests.get(yaml_file, stream=True)
    except requests.exceptions.MissingSchema:
        with open(yaml_file) as f:
            config = yaml.load(f)
    else:
        r.raw.decode_content = True
        config = yaml.load(r.raw)
    return config


def import_subclass(subclass_path, package=None, required_base_class=None):
    """
    Import and return a subclass.
    *subclass_path* must be in the form of 'module.subclass'.
    """
    module, _, subclass_name = subclass_path.rpartition('.')
    if package and not module.startswith('.'):
        module = '.' + module
    subclass = getattr(importlib.import_module(module, package), subclass_name)
    if required_base_class:
        assert issubclass(subclass, required_base_class), "Provided class is not a subclass of *required_base_class*"
    return subclass


def get_available_configs(config_dir, register=None):
    """
    Return (or update) a dictionary *register* that contains all config files in *config_dir*.
    """
    if register is None:
        register = dict()

    for config_file in os.listdir(config_dir):
        if config_file.startswith('_') or not config_file.lower().endswith('.yaml'):
            continue

        name = os.path.splitext(config_file)[0]
        config = load_yaml(os.path.join(config_dir, config_file))
        register[name] = config

    return register


def get_available_catalogs():
    """
    Return *available_catalogs* as a dictionary
    """
    return available_catalogs


def load_catalog_from_config_dict(catalog_config):
    """
    Load a galaxy catalog using a config dictionary.

    Parameters
    ----------
    catalog_config : dict
        a dictionary of config options

    Return
    ------
    galaxy_catalog : instance of a subclass of BaseGalaxyCatalog

    See also
    --------
    load_catalog()
    """
    return import_subclass(catalog_config['subclass_name'],
                           __package__,
                           BaseGenericCatalog)(**catalog_config)


def load_catalog(catalog_name, config_overwrite=None, check_version=True):
    """
    Load a galaxy catalog as specified in one of the yaml file in catalog_configs.

    Parameters
    ----------
    catalog_name : str
        name of the catalog (without '.yaml')
    config_overwrite : dict, optional
        a dictionary of config options to overwrite
    check_version : bool, optional
        whether or not to check if the current version is up-to-date.
        (Default: True)

    Return
    ------
    galaxy_catalog : instance of a subclass of BaseGalaxyCatalog
    """
    if catalog_name.lower().endswith('.yaml'):
        catalog_name = catalog_name[:-5]

    if catalog_name not in available_catalogs:
        raise KeyError("Catalog `{}` does not exist in the register. See `available_catalogs`.".format(catalog_name))

    config = available_catalogs[catalog_name]

    if check_version:
        try:
            online_config = load_yaml('{}/{}/{}.yaml'.format(_GITHUB_URL, _CONFIG_DIRNAME, catalog_name))
        except requests.RequestException:
            warnings.warn('Cannot retrive online config file. Skipping version check.')
        else:
            if config.get('version') != online_config.get('version'):
                warnings.warn('Catalog `{}` has a local version {} that differs from online version {}'.format(
                    catalog_name,
                    config.get('version'),
                    online_config.get('version'),
                ))

    if config_overwrite:
        config = config.copy()
        config.update(config_overwrite)

    return load_catalog_from_config_dict(config)


available_catalogs = get_available_configs(os.path.join(os.path.dirname(__file__), _CONFIG_DIRNAME))
