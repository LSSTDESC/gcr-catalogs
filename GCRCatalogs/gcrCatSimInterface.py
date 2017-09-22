"""
This script will define classes that enable CatSim to interface with GCR
"""

from collections import OrderedDict
import numpy as np
import gc
import numbers

_GCR_IS_AVAILABLE = True

try:
    from GCRCatalogs import load_catalog
except ImportError:
    _GCR_IS_AVAILABLE = False
    pass

try:
    from lsst.sims.utils import _angularSeparation
except ImportError:
    from astropy.coordinates import SkyCoord
    def _angularSeparation(ra1, dec1, ra2, dec2):
        return SkyCoord(ra1, dec1, unit="deg").separation(SkyCoord(ra2, dec2, unit="deg")).radian


__all__ = ["DESCQAObject"]

# a cache to store loaded catalogs to prevent them
# from being loaded more than once, eating up
# memory; this could happen since, for instance
# the same catalog will need to be queried twice
# go get bulges and disks from the same galaxy
_CATALOG_CACHE = {}

class DESCQAChunkIterator(object):
    """
    This class mimics the ChunkIterator defined and used
    by CatSim.  It accepts a query to the catalog reader
    and allows CatSim to iterate over it one chunk at a
    time.
    """

    def __init__(self, descqa_obj, column_map, obs_metadata,
                 colnames, default_values, chunk_size):
        """
        Parameters
        ----------
        descqa_obj is the DESCQA catalog being queried

        column_map is the columnMap defined in DESCQAObject
        which controls the mapping between DESCQA columns
        and CatSim columns

        obs_metadata is an ObservationMetaData (a CatSim class)
        defining the telescope orientation at the time of the
        simulated observation

        colnames lists the names of the quantities that need
        to be queried from descqa_obj. These will consist of
        column names that can be queried directly by passing
        them to descqa_obj.get_quantities() as well as column
        names that can be mapped using the DESCQAObject.columns
        mapping and columns defined the
        DESCQAObject.dbDefaultValues

        default_values is a dict (dbDefaultValues defined in the
        DESCQAObject) defining default column values to be used
        if the catalog does not contain required quantities

        chunk_size is an integer (or None) defining the number
        of rows to be returned at a time.
        """
        self._descqa_obj = descqa_obj
        self._catsim_colnames = colnames
        self._chunk_size = chunk_size
        self._data = None
        self._continue = True
        self._column_map = column_map
        self._obs_metadata = obs_metadata
        self._default_values = default_values

    def __iter__(self):
        return self

    def __next__(self):
        if self._data is None and self._continue:
            avail_qties = self._descqa_obj.list_all_quantities()
            avail_native_qties = self._descqa_obj.list_all_native_quantities()

            # find the list of names that need to be passed to self._descqa_obj.get_quantities()
            gcr_col_names = np.array([self._column_map[catsim_name][0] for catsim_name in self._catsim_colnames
                                      if self._column_map[catsim_name][0] in avail_qties
                                      or self._column_map[catsim_name][0] in avail_native_qties])

            gcr_col_names = np.unique(gcr_col_names)
            gcr_cat_data = self._descqa_obj.get_quantities(gcr_col_names)

            n_rows = len(gcr_cat_data[gcr_col_names[0]])

            # now build a dict keyed to the row names in self._catsim_colnames
            # whose values are the numpy arrays of data corresponding to those
            # column names
            catsim_data = {}
            dtype_list = []
            for catsim_name in self._catsim_colnames:
                gcr_name = self._column_map[catsim_name][0]

                if gcr_name in avail_qties or gcr_name in avail_native_qties:
                    catsim_data[catsim_name] = gcr_cat_data[gcr_name]
                else:
                    catsim_data[catsim_name] = np.array([self._default_values[gcr_name]]*n_rows)

                if len(self._column_map[catsim_name])>1:
                    catsim_data[catsim_name] = self._column_map[catsim_name][1](catsim_data[catsim_name])
                dtype_list.append((catsim_name, catsim_data[catsim_name].dtype))

            dtype = np.dtype(dtype_list)

            del gcr_cat_data
            gc.collect()

            # if an ObservationMetaData has been specified, cull
            # the data to be within the field of view
            if self._obs_metadata is not None:
                if self._obs_metadata._boundLength is not None:
                    if not isinstance(self._obs_metadata._boundLength, numbers.Number):
                        radius_rad = max(self._obs_metadata._boundLength[0],
                                         self._obs_metadata._boundLength[1])
                    else:
                        radius_rad = self._obs_metadata._boundLength

                    valid = np.where(_angularSeparation(catsim_data['raJ2000'],
                                                        catsim_data['decJ2000'],
                                                        self._obs_metadata._pointingRA,
                                                        self._obs_metadata._pointingDec) < radius_rad)

                    for name in catsim_data:
                        catsim_data[name] = catsim_data[name][valid]

            # convert catsim_data into a numpy recarray, which is what
            # CatSim ultimately expects the ChunkIterator to deliver
            records = []
            for i_rec in range(len(catsim_data[self._catsim_colnames[0]])):
                rec = (tuple([catsim_data[name][i_rec]
                              for name in self._catsim_colnames]))
                records.append(rec)

            if len(records) == 0:
                self._data = np.recarray(shape=(0,len(catsim_data)), dtype=dtype)
            else:
                self._data = np.rec.array(records, dtype=dtype)
            self._start_row = 0

        # iterate over the chunks of the recarray stored in self._data
        if self._chunk_size is None and self._continue and len(self._data)>0:
            output = self._data
            self._data = None
            self._continue = False
            return output
        elif self._continue:
            if self._start_row<len(self._data):
                old_start = self._start_row
                self._start_row += self._chunk_size
                return self._data[old_start:self._start_row]
            else:
                self._data = None
                self._continue = False
                raise StopIteration

        raise StopIteration



class DESCQAObject(object):
    """
    This class is meant to mimic the CatalogDBObject usually used to
    connect CatSim to a database.
    """

    idColKey = None
    objectTypeId = None
    verbose = False

    def __init__(self, yaml_file_name):
        """
        Parameters
        ----------
        yaml_file_name is the name of the yaml file that will tell DESCQA
        how to load the catalog
        """

        global _GCR_IS_AVAILABLE
        if not _GCR_IS_AVAILABLE:
            raise RuntimeError("You cannot use DESQAObject\n"
                               "You do not have the generic catalog reader "
                               "installed and setup")

        global _CATALOG_CACHE
        if yaml_file_name in _CATALOG_CACHE:
            self._catalog = _CATALOG_CACHE[yaml_file_name]
        else:
            self._catalog = load_catalog(yaml_file_name)
            _CATALOG_CACHE[yaml_file_name] = self._catalog

        self.columnMap = None
        self._make_column_map()

    def getIdColKey(self):
        return self.idColKey

    def getObjectTypeId(self):
        return self.objectTypeId

    def _make_column_map(self):
        """
        Slightly different from the database case.
        self.columnMap will be a dict keyed on the CatSim column name.
        The values will be tuples.  The first element of the tuple is the
        GCR column name corresponding to that CatSim column.  The second
        element is an (optional) transformation applied to the GCR column
        used to get it into units expected by CatSim.
        """
        self.columnMap = OrderedDict()

        if hasattr(self, 'columns'):
            for column_tuple in self.columns:
                if len(column_tuple)>1:
                    self.columnMap[column_tuple[0]] = column_tuple[1:]

        for name in self._catalog.list_all_quantities():
            if name not in self.columnMap:
                self.columnMap[name] = (name,)

        for name in self._catalog.list_all_native_quantities():
            if name not in self.columnMap:
                self.columnMap[name] = (name,)

        if hasattr(self, 'dbDefaultValues'):
            for name in self.dbDefaultValues:
                if name not in self.columnMap:
                    self.columnMap[name] = (name,)


    def query_columns(self, colnames=None, chunk_size=None,
                      obs_metadata=None, constraint=None, limit=None):
        """
        Parameters
        ----------
        colnames is a list of column names to be queried (CatSim
        will determine which automaticall)

        chunk_size is the number of rows to return at a time

        obs_metadata is an ObservationMetaData defining the orientation
        of the telescope

        constraint is ignored, but needs to be here to preserve the API

        limit is ignored, but needs to be here to preserve the API
        """

        if self.objectTypeId is None:
            raise RuntimeError("Need to define objectTypeId for your DESCQAObject")

        if self.idColKey is None:
            raise RuntimeError("Need to define idColKey for your DESCQAObject")

        if colnames is None:
            colnames = [k for k in self.columnMap]

        if hasattr(self, 'dbDefaultValues'):
            default = self.dbDefaultValues
        else:
            default = None

        return DESCQAChunkIterator(self._catalog, self.columnMap, obs_metadata,
                                   colnames, default, chunk_size)
