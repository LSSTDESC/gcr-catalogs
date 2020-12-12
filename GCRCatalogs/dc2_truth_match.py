"""
Reader for truth-match catalogs persisted as parquet files and partitioned in tracts.
"""
import numpy as np
import astropy.units as u

from .dc2_dm_catalog import DC2DMTractCatalog

__all__ = ["DC2TruthMatchCatalog"]


def _flux_to_mag(flux):
    with np.errstate(divide="ignore"):
        return (flux * u.nJy).to_value(u.ABmag)  # pylint: disable=no-member


class DC2TruthMatchCatalog(DC2DMTractCatalog):
    r"""
    DC2 Truth-Match (parquet) Catalog reader

    This reader is intended for reading the truth-match catalog that is in
    parquet format and partitioned by tracts.

    Two options, `as_object_addon` and `as_truth_table` further control,
    respectively, whether the returned table contains only rows that match
    to the object catalog (`as_object_addon=True`), or only unique truth
    entries (`as_truth_table=True`).

    When `as_object_addon` is set, most column names will also be decorated
    with a `_truth` postfix.

    The underlying truth-match catalog files contain fluxes but not magnitudes.
    The reader provides translation to magnitude (using `_flux_to_mag`) for
    convenience. No other translation is applied.

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
            no_postfix = ("truth_type", "is_unique_truth_entry", "match_sep", "match_objectId")
            self._quantity_modifiers = {
                (k + ("" if k in no_postfix else "_truth")): (v or k) for k, v in self._quantity_modifiers.items()
            }

    def _obtain_native_data_dict(self, native_quantities_needed, native_quantity_getter):
        """
        When `as_object_addon` or `as_truth_table` is set, we need to filter the table
        based on `match_objectId` or `is_unique_truth_entry` before the data is returned .
        To achieve such, we have to overwrite this method to inject the additional columns
        and to apply the masks.
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