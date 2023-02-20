"""
Base filters. To be called by high-level helper functions that are specific
to catalog types (e.g., tract catalogs).
"""

import numpy as np

from GCR import GCRQuery

__all__ = ["partition_filter", "sample_filter"]


def partition_filter(partition_name, ids, id_high=None):
    """
    Returns a GCRQuery object to be used in the `native_filters` argument of get_quantities(),
    to select a subset of partitions.

    *partition_name* must be a "native filter quantity" in GCR,
    and the partitions must be specified by integer IDs.
    Existing examples include "tract" for object catalogs and "healpix_pixel" for cosmoDC2.

    If *ids* is a single integer, select only that partition.
    If *ids* and *id_high* are both given as single integers, select [ids, id_high]
    (inclusive on both ends!).
    If *ids* is a list, select partitions in that list (*id_high* is ignored).
    """
    if isinstance(ids, int):
        if id_high is None:
            return GCRQuery(f"{partition_name} == {ids}")
        elif isinstance(id_high, int):
            return GCRQuery(f"{partition_name} >= {ids}", f"{partition_name} <= {id_high}")
        raise ValueError(f"When `{partition_name}s` is an integer, `{partition_name}_high` must be an integer or None.")

    ids = np.unique(np.asarray(ids, dtype=int))
    if not ids.size:
        raise ValueError(f"Must select at least one {partition_name}.")

    def _partition_selector(partition_ids, ids_to_select=ids):
        return np.isin(partition_ids, ids_to_select, assume_unique=True)

    return GCRQuery((_partition_selector, partition_name))


def sample_filter(ref_col_name, frac, random_state=None):
    """
    Returns a GCRQuery object to be used in the `filters` argument of get_quantities()
    to randomly sample the object catalog by a given fraction (*frac*).

    *ref_col_name* must be a column of integer values.

    Optionally, provide *random_state* (int or np.random.RandomState) to fix random state.
    """
    # pylint: disable=no-member

    frac = float(frac)
    if frac > 1 or frac < 0:
        raise ValueError("`frac` must be a float number in [0, 1].")
    if frac == 1:
        return GCRQuery()
    if frac == 0:
        return GCRQuery((lambda a: np.zeros_like(a, dtype=bool), ref_col_name))

    if not isinstance(random_state, np.random.RandomState):
        random_state = np.random.RandomState(random_state)
    seed = random_state.randint(2**32)

    def _sampler(arr, frac=frac, seed=seed):
        size = len(arr)  # arr is a numpy array of integers
        if size:
            return np.random.RandomState((int(arr[0]) + seed) % (2**32)).rand(size) < frac
        return np.zeros(0, dtype=bool)

    return GCRQuery((_sampler, ref_col_name))
