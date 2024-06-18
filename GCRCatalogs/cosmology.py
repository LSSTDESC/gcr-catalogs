import inspect
import astropy.cosmology

__all__ = ["FlatLambdaCDM"]

_cosmo_astropy_allowed = inspect.getfullargspec(astropy.cosmology.FlatLambdaCDM).args

class FlatLambdaCDM(astropy.cosmology.FlatLambdaCDM):
    def __init__(self, **kwargs):
        cosmo_astropy = dict()
        for k, v in kwargs.items():
            if k in _cosmo_astropy_allowed:
                cosmo_astropy[k] = v
            else:
                setattr(self, k, v)
        super().__init__(**cosmo_astropy)
