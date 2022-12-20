"""
Reader for truth-match catalogs persisted as parquet files and partitioned in tracts.
"""
import os

import numpy as np
import astropy.units as u

from .dc2_dm_catalog import DC2DMTractCatalog

__all__ = ["DC2TruthMatchCatalog"]

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
META_PATH = os.path.join(FILE_DIR, 'catalog_configs/_dc2_truth_match_meta.yaml')


def _flux_to_mag(flux):
    with np.errstate(divide="ignore"):
        mag = (flux * u.nJy).to_value(u.ABmag)  # pylint: disable=no-member
    mag[~np.isfinite(mag)] = np.nan  # homogenize inf and nan
    return mag


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
    base_dir            (str): Directory of data files being served, required
    filename_pattern    (str): The optional regex pattern of served data files
    as_object_addon    (bool): If set, return rows in the the same row order as object catalog
    as_truth_table     (bool): If set, remove duplicated truth rows
    as_matchdc2_schema (bool): If set, use column names in Javi's matchDC2 catalog.
    """

    def _subclass_init(self, **kwargs):
        self.META_PATH = META_PATH

        super()._subclass_init(**dict(kwargs, is_dpdd=True))  # set is_dpdd=True to obtain bare modifiers

        self._as_object_addon = bool(kwargs.get("as_object_addon"))
        self._as_truth_table = bool(kwargs.get("as_truth_table"))
        self._as_matchdc2_schema = bool(kwargs.get("as_matchdc2_schema"))
        if self._as_matchdc2_schema:
            self._as_object_addon = True

        if self._as_object_addon and self._as_truth_table:
            raise ValueError("Reader options `as_object_addon` and `as_truth_table` cannot both be set to True.")

        if self._as_matchdc2_schema:
            self._use_matchdc2_quantity_modifiers()
            return

        flux_cols = [k for k in self._quantity_modifiers if k.startswith("flux_")]
        for col in flux_cols:
            self._quantity_modifiers["mag_" + col.partition("_")[2]] = (_flux_to_mag, col)

        if self._as_object_addon:
            no_postfix = ("truth_type", "match_objectId", "match_sep", "is_good_match", "is_nearest_neighbor", "is_unique_truth_entry")
            self._quantity_modifiers = {
                (k + ("" if k in no_postfix else "_truth")): (v or k) for k, v in self._quantity_modifiers.items()
            }

    def _detect_available_bands(self):
        return ["_".join(col.split("_")[1:-1]) for col in self._columns if col.startswith('flux_') and col.endswith('_noMW')]

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
            n = np.count_nonzero(d["match_objectId"].values > -1)
            return {c: d[c].values[:n] for c in columns}
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

    def _use_matchdc2_quantity_modifiers(self):
        """
        To recreate column names in dc2_matched_table.py
        cf. https://github.com/fjaviersanchez/MatchDC2/blob/master/python/matchDC2.py
        """

        quantity_modifiers = {
            "truthId": (lambda i, t: np.where(t < 3, i, "-1").astype(np.int64), "id", "truth_type"),
            "objectId": "match_objectId",
            "is_matched": "is_good_match",
            "is_star": (lambda t: t > 1, "truth_type"),
            "ra": "ra",
            "dec": "dec",
            "redshift_true": "redshift",
            "dist": "match_sep",
        }

        for col in self._columns:
            if col.startswith("flux_") and col.endswith("_noMW"):
                quantity_modifiers["mag_" + col.split("_")[1] + "_lsst"] = (_flux_to_mag, col)

        quantity_modifiers['galaxy_match_mask'] = (lambda t, m: (t == 1) & m, "truth_type", "is_good_match")
        quantity_modifiers['star_match_mask'] = (lambda t, m: (t == 2) & m, "truth_type", "is_good_match")

        # put these into self for `self.add_derived_quantity` to work
        self._quantity_modifiers = quantity_modifiers
        self._native_quantities = set(self._columns)

        for col in list(quantity_modifiers):
            if col in ("is_matched", "is_star", "galaxy_match_mask", "star_match_mask"):
                continue
            for t in ("galaxy", "star"):
                self.add_derived_quantity(
                    "{}_{}".format(col, t),
                    lambda d, m: np.ma.array(d, mask=m),
                    col,
                    "{}_match_mask".format(t),
                )

    def _get_quantity_info_dict(self, quantity, default=None):
        """
        Befere calling the parent method, check if `quantity` has an added "_truth" postfix
        due to the `if self._as_object_addon:...` part in _subclass_init. If so, remove the postfix.
        """
        if (
            quantity not in self._quantity_info_dict and
            quantity in self._quantity_modifiers and
            quantity.endswith("_truth")
        ):
            quantity = quantity[:-6]
        return super()._get_quantity_info_dict(quantity, default)
