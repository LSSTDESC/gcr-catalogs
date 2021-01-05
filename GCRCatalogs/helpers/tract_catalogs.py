"""
Helper functions for tract catalogs.
"""

import numpy as np

from GCR import GCRQuery

__all__ = ["tract_filter", "sample_filter"]


def tract_filter(tracts, tract_high=None):
    """
    Returns a GCRQuery object to be used in the `native_filters` argument of get_quantities(),
    to select only the tracts in *tracts* (a list of integers).

    If *tracts* is a single integer, select only that tract.
    If *tracts* and *tract_high* are both given as single integers, select [tracts, tract_high]
    (inclusive on both ends!).
    """
    if isinstance(tracts, int):
        if tract_high is None:
            return GCRQuery('tract == {}'.format(tracts))
        elif isinstance(tract_high, int):
            return GCRQuery('tract >= {}'.format(tracts), 'tract <= {}'.format(tract_high))
        raise ValueError("When `tracts` is an integer, `tract_high` must be an integer or None.")

    tracts = np.unique(np.asarray(tracts, dtype=np.int))
    if not tracts.size:
        raise ValueError("Must select at least one tract.")

    def _tract_selector(tract, tracts_to_select=tracts):
        return np.in1d(tract, tracts_to_select, assume_unique=True)

    return GCRQuery((_tract_selector, "tract"))


def sample_filter(frac, random_state=None):
    """
    Returns a GCRQuery object to be used in the `filters` argument of get_quantities()
    to randomly sample the object catalog by a given fraction (*frac*).

    Optionally, provide *random_state* (int or np.random.RandomState) to fix random state.
    """
    # pylint: disable=no-member

    frac = float(frac)
    if frac > 1 or frac < 0:
        raise ValueError("`frac` must be a float number in [0, 1].")
    if frac == 1:
        return GCRQuery()
    if frac == 0:
        return GCRQuery((lambda a: np.zeros_like(a, dtype=np.bool), "tract"))

    if not isinstance(random_state, np.random.RandomState):
        random_state = np.random.RandomState(random_state)
    seed = random_state.randint(65536)

    def _sampler(tract_arr, frac=frac, seed=seed):
        size = len(tract_arr)  # tract_arr is a numpy array of tract IDs
        if size:
            return np.random.RandomState(tract[0] + seed).rand(size) < frac
        return np.zeros(0, dtype=np.bool)

    return GCRQuery((_sampler, "tract"))
