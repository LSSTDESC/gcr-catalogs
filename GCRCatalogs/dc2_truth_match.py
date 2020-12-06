"""
Reader for truth-match catalogs persisted as parquet files and partitioned in tracts.
"""
import numpy as np
import astropy.units as u

from .dc2_dm_catalog import DC2DMTractCatalog

__all__ = ["DC2TruthMatchCatalog"]


def _flux_to_mag(flux):
    return (flux * u.nJy).to_value(u.ABmag)  # pylint: disable=no-member


class DC2TruthMatchCatalog(DC2DMTractCatalog):
    r"""
    DC2 Truth-Match (parquet) Catalog reader

    Presents tables exactly as they are defined in the files (no aliases,
    no derived quantities)

    Parameters
    ----------
    base_dir          (str): Directory of data files being served, required
    filename_pattern  (str): The optional regex pattern of served data files
    as_object_addon  (bool): If set, return rows in the the same row order as object catalog
    as_truth_table   (bool): If set, remove duplicated truth rows
    """

    def _subclass_init(self, **kwargs):

        super()._subclass_init(**dict(kwargs, is_dpdd=True))  # set is_dpdd=True to obtain bare modifiers

        self._as_object_addon = bool(kwargs.get("as_object_addon"))
        self._as_truth_table = bool(kwargs.get("as_truth_table"))
        if self._as_object_addon and self._as_truth_table:
            raise ValueError("Reader options `as_object_addon` and `as_truth_table` cannot both be set to True.")

        flux_cols = [k for k in self._quantity_modifiers if k.startswith("flux_")]
        for col in flux_cols:
            self._quantity_modifiers["mag_" + col.partition("_")[2]] = (_flux_to_mag, col)

        if self._as_object_addon:
            self._quantity_modifiers = {(k + "_truth"): v for k, v in self._quantity_modifiers.items()}

    def _obtain_native_data_dict(self, native_quantities_needed, native_quantity_getter):
        """
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        native_quantities_needed = set(native_quantities_needed)
        if self._as_object_addon:
            native_quantities_needed.add("match_objectId")
        elif self._as_truth_table:
            native_quantities_needed.add("is_unique_truth_entry")

        columns = list(native_quantities_needed)
        d = native_quantity_getter.read_columns(columns, as_dict=False)
        if self._as_object_addon:
            mask = d["match_objectId"].values > -1
            return {c: d[c].values[mask] for c in columns}
        elif self._as_truth_table:
            mask = d["is_unique_truth_entry"].values
            return {c: d[c].values[mask] for c in columns}
        return {c: d[c].values for c in columns}

    def __len__(self):
        if self._len is None:
            # pylint: disable=attribute-defined-outside-init
            if self._as_object_addon:
                self._len = sum(
                    np.count_nonzero(d["match_objectId"] > -1)
                    for d in self.get_quantities(["match_objectId"], return_iterator=True)
                )
            elif self._as_truth_table:
                self._len = sum(
                    np.count_nonzero(d["is_unique_truth_entry"])
                    for d in self.get_quantities(["is_unique_truth_entry"], return_iterator=True)
                )
            else:
                self._len = sum(len(dataset) for dataset in self._datasets)
        return self._len
