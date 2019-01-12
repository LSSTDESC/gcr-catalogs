from __future__ import division, print_function
import numpy as np
import pandas as pd
import yaml
from GCR import BaseGenericCatalog
from lsst.daf.persistence import Butler

__all__ = ['SingleVisitCatalog']

available_filters = ['u', 'g', 'r', 'i', 'z', 'y']

def asDict(cat, cls=None, copy=False, unviewable="copy"):
    """
    Function to return a dicionary view into a DM catalog.

    **This function is a simple modification of the exisiting asAstropy**
    http://doxygen.lsst.codes/stack/doxygen/x_masterDoxyDoc/classlsst_1_1afw_1_1table_1_1base_1_1base_continued_1_1_catalog.html#af891786464b1e84c7f56af0101212e95
    
    Args:
    -----
    cat: SourceCatalog
         Input SourceCatalog object
    
    copy: bool
          Whether to copy data from the LSST catalog to the pandas dataframe.

    unviewable  One of the following options, indicating how to handle field types
                            (string and Flag) for which views cannot be constructed:
                              - 'copy' (default): copy only the unviewable fields.
                              - 'raise': raise ValueError if unviewable fields are present.
                              - 'skip': do not include unviewable fields in the Astropy Table.
                            This option is ignored if copy=True.
    """
 
    columns=dict()
    if unviewable not in ("copy", "raise", "skip"):
        raise ValueError("'unviewable' must be one of 'copy', 'raise', or 'skip'")
    ps = cat.getMetadata()
    meta = ps.toOrderedDict() if ps is not None else None
    items = cat.schema.extract("*", ordered=True)
    for name, item in items.items():
        key = item.key
        unit = item.field.getUnits() or None  # use None instead of "" when empty
        if key.getTypeString() == "String":
            if not copy:
                if unviewable == "raise":
                    raise ValueError("Cannot extract string unless copy=True or unviewable='copy' or 'skip'.")
                elif unviewable == "skip":
                    continue
            data = numpy.zeros(len(cat), dtype=numpy.dtype((str, key.getSize())))
            for i, record in enumerate(cat):
                data[i] = record.get(key)
        elif key.getTypeString() == "Flag":
            if not copy:
                if unviewable == "raise":
                    raise ValueError(
                        "Cannot extract packed bit columns unless copy=True or unviewable='copy' or 'skip'."
                    )
                elif unviewable == "skip":
                    continue
            data = cat.columns.get_bool_array(key)
        elif key.getTypeString() == "Angle":
            data = cat.columns.get(key)
            unit = "radian"
            if copy:
                data = data.copy()
        else:
            data = cat.columns.get(key)
            if copy:
                data = data.copy()
        columns.update({name:data})
    return columns

def append_dict(dict1,dict2):
    try:
        assert(dict1.keys() == dict2.keys())
    except AssertionError:
        print('The dictionaries should have the same keys')

    for key in dict1.keys():
        dict1[key] = np.concatenate([dict1[key], dict2[key]]).ravel()
    return dict1

class SingleVisitCatalog(BaseGenericCatalog):
    """
    Reader for single visit catalogs (src catalog)
    
    Args:
    -----
    
    repo_path: str
        path to repository containing the DM-processed data.

    filter_band: str
        name of the filter (band) in which the user want to perform the query
        it can only take the value u, g, r, i, z, y.
    
    visit: int
        visit number to query. If `None` all the available visits in the 
        requested band will be queried. 
  
    detector_number: int
        detector number to query (from 0 to 188). If `None` all the available
        sensors in the requested visit(s) will be queried.
    """

    def _subclass_init(self, repo_path, filter_band, visit=None,
                        detector=None, **kwargs):
       
        if filter_band in available_filters:
            self.band = filter_band      
        else:
            raise Exception('filter_band should be one of the LSST filters (u,g,r,i,z,y)')
        if (detector is not None) & (detector not in np.arange(0,189)):
            raise Exception('detector should be None or an integer in the range [0,189)')
        else:
            self.detector = detector
        self.visit = visit
        self.butler = Butler(repo_path)
        self.visit_list = []
        self._data = dict()
        self._files = dict()
        _all_visits = self.butler.subset('src').cache # Create list of all src catalogs (single-visit) in a given repo
        # We create and fill the list of visits to query
        for visitId in _all_visits:
            if visitId['filter']==self.band:
                if (visit is None) | (visitId['visit']==visit):
                    if (detector is None) | (visitId['detector']==detector):
                        self.visit_list.append(visitId)

    def _read_visit(self, visitId, **kwargs):
        return asDict(self.butler.get('src', visitId))

    def _load_single_catalog(self, visit_list, **kwargs): 
        for i, visitId in enumerate(visit_list):
            if i==0:
               self._data = self._read_visit(visitId)
            else:
               self._data = append_dict(self._data,self._read_visit(visitId))
        return self._data
    
    def load_single_catalog(self, **kwargs):
        return self._load_single_catalog(self.visit_list)

    def _native_quantity_getter(self, native_quantity):
        return self._data[native_quantity]
    
    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise ValueError('`native_filters` is not supported')
        yield self._native_quantity_getter

    def _generate_native_quantity_list(self):
        return self.load_single_catalog().keys() # All files have the same exact columns 
