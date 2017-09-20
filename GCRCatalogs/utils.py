import yaml
import requests

__all__ = ['load_yaml']

def load_yaml(yaml_file):
    """
    Load yaml file
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
