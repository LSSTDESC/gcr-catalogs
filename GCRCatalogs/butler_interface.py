"""
butler interface
"""
from GCR import BaseGenericCatalog

_HAS_LSST_STACK = True
try:
    from lsst.daf.persistence import Butler, NoResults
    from lsst.afw.image import Calib
except ImportError:
    _HAS_LSST_STACK = False

__all__ = ['SimpleButlerInterface', 'SingleVisitCatalog']

# pylint: disable=W0221

class SimpleButlerInterface(BaseGenericCatalog):
    """
    A simple butler interface.

    Args:
    -----
    repo: str
        path to repository containing the DM-processed data.
    dataId: dict
    """

    def _subclass_init(self, repo, datasetType, dataId=None, **kwargs):

        if not _HAS_LSST_STACK:
            raise RuntimeError('LSST Stack not available')

        self._butler = Butler(repo)
        self._datasetType = datasetType
        self._dataId_cache = self._butler.subset(self._datasetType, dataId=dataId).cache

        self._columns = None
        for dataId in self._dataId_cache:
            data = self._get_data(dataId)
            if data is not None:
                self._columns = data.schema.getNames()
                break

        if not self._columns:
            raise RuntimeError('No datasets or columns found!')

    def _get_data(self, dataId, datasetType=None):
        try:
            data = self._butler.get(datasetType or self._datasetType, dataId=dataId)
        except NoResults:
            return None
        return data

    def _iter_native_dataset(self, native_filters=None):
        for dataId in self._dataId_cache:
            if native_filters is None or native_filters.check_scalar(dataId):
                data = self._get_data(dataId)
                if data is not None:
                    yield data.get

    def _generate_native_quantity_list(self):
        return self._columns


class SingleVisitCatalog(SimpleButlerInterface):
    """
    Reader for single visit catalogs (src catalog)

    Args:
    -----
    repo: str
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

    def _subclass_init(self, repo, filter_band, visit, detector=None, **kwargs):

        dataId = {'filter': filter_band, 'visit': int(visit)}
        if detector is not None:
            dataId['detector'] = int(detector)

        super()._subclass_init(repo, 'src', dataId, **kwargs)

        self._calib = None
        for dataId in self._dataId_cache:
            calexp_md = self._get_data(dataId, 'calexp_md')
            if calexp_md is not None:
                self._calib = Calib(calexp_md)
                break

        if self._calib is not None:
            self._calib.setThrowOnNegativeFlux(False)
            self._quantity_modifiers = {
                c.replace('instFlux', 'mag'): (self._calib.getMagnitude, c) \
                for c in self._columns if 'instFlux' in c
            }
