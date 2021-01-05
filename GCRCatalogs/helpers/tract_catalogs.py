"""
Helper functions for tract catalogs.
"""
from . import base_filters

__all__ = ["tract_filter", "sample_filter"]


def tract_filter(tracts, tract_high=None):
    """
    Returns a GCRQuery object to be used in the `native_filters` argument of get_quantities(),
    to select only the tracts in *tracts* (a list of integers).

    If *tracts* is a single integer, select only that tract.
    If *tracts* and *tract_high* are both given as single integers, select [tracts, tract_high]
    (inclusive on both ends!).
    """
    return base_filters.partition_filter("tract", tracts, tract_high)


def sample_filter(frac, random_state=None):
    """
    Returns a GCRQuery object to be used in the `filters` argument of get_quantities()
    to randomly sample the object catalog by a given fraction (*frac*).

    Optionally, provide *random_state* (int or np.random.RandomState) to fix random state.
    """
    return base_filters.sample_filter("tract", frac, random_state)
