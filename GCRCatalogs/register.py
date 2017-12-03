import os
import importlib
import warnings
import yaml
import requests
from GCR import BaseGenericCatalog


__all__ = ['available_catalogs', 'get_catalog_config', 'get_available_catalogs', 'load_catalog']

_CONFIG_DIRNAME = 'catalog_configs'
_GITHUB_URL = 'https://raw.githubusercontent.com/LSSTDESC/gcr-catalogs/master/GCRCatalogs'


def load_yaml(yaml_file):
    """
    Load *yaml_file*. Ruturn a dictionary.
    """
    try:
        r = requests.get(yaml_file, stream=True)
    except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired):
        with open(yaml_file) as f:
            config = yaml.load(f)
    else:
        if r.status_code == 404:
            raise requests.RequestException('404 Not Found!')
        r.raw.decode_content = True
        config = yaml.load(r.raw)
    return config


def strip_yaml_extension(filename):
    """
    remove ending '.yaml' in *filename*
    """
    return filename[:-5] if filename.lower().endswith('.yaml') else filename


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

        name = strip_yaml_extension(config_file)
        config = load_yaml(os.path.join(config_dir, config_file))
        register[name] = config

    return register


def resolve_config_alias(config_dict, last_alias=None):
    """
    resolve the alias in *config_dict* and return resolved config dict
    """
    if config_dict.get('alias'):
        alias = strip_yaml_extension(config_dict.get('alias', ''))
        if alias not in available_catalogs:
            raise KeyError('Catalog {} does not exist in available catalogs.'.format(alias))
        if last_alias and last_alias == alias:
            raise ValueError('alias points to itself!')
        return resolve_config_alias(available_catalogs[alias], alias)
    return config_dict


def get_catalog_config(catalog):
    """
    get the config dict of *catalog*
    """
    return resolve_config_alias(available_catalogs[catalog])


def get_available_catalogs(include_default_only=True):
    """
    Return *available_catalogs* as a dictionary

    If *include_default_only* is set to False, return all catalogs.
    """
    return _available_catalogs_default if include_default_only else available_catalogs


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


def load_catalog(catalog_name, config_overwrite=None):
    """
    Load a galaxy catalog as specified in one of the yaml file in catalog_configs.

    Parameters
    ----------
    catalog_name : str
        name of the catalog (without '.yaml')
    config_overwrite : dict, optional
        a dictionary of config options to overwrite

    Return
    ------
    galaxy_catalog : instance of a subclass of BaseGalaxyCatalog
    """
    catalog_name = strip_yaml_extension(catalog_name)

    if catalog_name not in available_catalogs:
        raise KeyError("Catalog `{}` does not exist in the register. See `available_catalogs`.".format(catalog_name))

    config = available_catalogs[catalog_name]

    if config.get('alias'):
        if strip_yaml_extension(config.get('alias', '')) == catalog_name:
            raise ValueError('Oops, config {} alias itself!'.format(catalog_name))
        url = '{}/{}/{}.yaml'.format(_GITHUB_URL, _CONFIG_DIRNAME, catalog_name)
        try:
            online_config = load_yaml(url)
        except (requests.RequestException, yaml.error.YAMLError):
            warnings.warn('Version check skipped. Not able to retrive or load online config file {}'.format(url))
        else:
            if config['alias'] != online_config.get('alias'):
                warnings.warn('`{}` points to local version `{}`, differs from online version `{}`'.format(
                    catalog_name,
                    config['alias'],
                    online_config.get('alias'),
                ))

        return load_catalog(config['alias'], config_overwrite)

    if config_overwrite:
        if 'alias' in config_overwrite:
            raise ValueError('`config_overwrite` cannot specify `alias`!')
        config = config.copy()
        config.update(config_overwrite)

    return load_catalog_from_config_dict(config)


available_catalogs = get_available_configs(os.path.join(os.path.dirname(__file__), _CONFIG_DIRNAME))
_available_catalogs_default = {k: resolve_config_alias(v) for k, v in available_catalogs.items() if v.get('included_by_default')}
