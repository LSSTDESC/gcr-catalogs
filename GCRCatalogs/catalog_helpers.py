import importlib
import yaml
import requests

__all__ = ["load_yaml_local", "load_yaml", "load_yaml_buf",
           "import_subclass"]


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


def load_yaml_buf(b):
    return yaml.safe_load(b)


# catalog loading helper functions
def import_subclass(subclass_path, package="GCRCatalogs",
                    required_base_class=None):
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
