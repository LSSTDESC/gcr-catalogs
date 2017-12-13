"""
This script will define classes that enable CatSim to interface with GCR
"""
import numpy as np

__all__ = ["DESCQAObject", "bulgeDESCQAObject", "diskDESCQAObject"]


_GCR_IS_AVAILABLE = True
try:
    from GCR import dict_to_numpy_array
    import GCRCatalogs
except ImportError:
    _GCR_IS_AVAILABLE = False

_LSST_IS_AVAILABLE = True
try:
    from lsst.sims.utils import _angularSeparation
except ImportError:
    _LSST_IS_AVAILABLE = False
    from astropy.coordinates import SkyCoord
    def _angularSeparation(ra1, dec1, ra2, dec2):
        return SkyCoord(ra1, dec1, unit="radian").separation(SkyCoord(ra2, dec2, unit="radian")).radian

def arcsec_to_radians(x):
    return np.deg2rad(x/3600.0)


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

    def __init__(self, descqa_obj, column_map=None, obs_metadata=None,
                 colnames=None, default_values=None, chunk_size=None):
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

        default_values is ignored.

        chunk_size is an integer (or None) defining the number
        of rows to be returned at a time.
        """
        self._descqa_obj = descqa_obj
        self._obs_metadata = obs_metadata
        self._column_map = column_map or dict()

        if colnames is None:
            self._colnames = list(self._column_map)
            self._colnames += list(self._descqa_obj.list_all_quantities(include_native=True))
        else:
            self._colnames = list(colnames)

        self._chunk_size = int(chunk_size) if chunk_size else None
        self._chunk_slice = slice(None, self._chunk_size)
        self._data_indices = None

        assert self._descqa_obj.has_quantities([self._column_map.get(name, name) for name in self._colnames]),\
                "some quantities do not exist!!"

    def __iter__(self):
        return self

    next = __next__

    def __next__(self):
        if self._data_indices is None:
            self._init_data_indices()

        if len(self._data_indices) == 0:
            raise StopIteration

        data = {}
        for name in self._colnames:
            gcr_name = self._column_map.get(name, name)
            data[name] = self._descqa_obj[gcr_name][self._data_indices[self._chunk_slice]]

        self._data_indices = self._data_indices[self._chunk_size:] if self._chunk_size else []

        return dict_to_numpy_array(data)


    def _init_data_indices(self):

        if self._obs_metadata is not None and self._obs_metadata._boundLength is not None:
            try:
                radius_rad = max(self._obs_metadata._boundLength[0],
                                 self._obs_metadata._boundLength[1])
            except TypeError:
                radius_rad = self._obs_metadata._boundLength

            ra = self._descqa_obj['raJ2000']
            dec = self._descqa_obj['decJ2000']

            self._data_indices = np.where(_angularSeparation(ra, dec, \
                    self._obs_metadata._pointingRA, \
                    self._obs_metadata._pointingDec) < radius_rad)[0]

        else:
            self._data_indices = np.arange(len(self._descqa_obj['raJ2000']))



class DESCQAObject(object):
    """
    This class is meant to mimic the CatalogDBObject usually used to
    connect CatSim to a database.
    """

    objectTypeId = None
    verbose = False

    epoch = 2000.0
    idColKey = 'galaxy_id'
    columns_need_postfix = ('majorAxis', 'minorAxis', 'sindex')
    postfix = None

    def __init__(self, yaml_file_name, config_overwrite=None):
        """
        Parameters
        ----------
        yaml_file_name is the name of the yaml file that will tell DESCQA
        how to load the catalog
        """

        if not _GCR_IS_AVAILABLE:
            raise RuntimeError("You cannot use DESQAObject\n"
                               "You do not have *GCR* installed and setup")

        if yaml_file_name not in _CATALOG_CACHE:
            _CATALOG_CACHE[yaml_file_name] = GCRCatalogs.load_catalog(yaml_file_name, config_overwrite)

        self._catalog = _CATALOG_CACHE[yaml_file_name]
        self.columnMap = None

        self._catalog.add_modifier_on_derived_quantities('raJ2000', np.deg2rad, 'ra_true')
        self._catalog.add_modifier_on_derived_quantities('decJ2000', np.deg2rad, 'dec_true')

        self._catalog.add_quantity_modifier('redshift', self._catalog.get_quantity_modifier('redshift_true'), overwrite=True)
        self._catalog.add_quantity_modifier('gamma1', self._catalog.get_quantity_modifier('shear_1'))
        self._catalog.add_quantity_modifier('gamma2', self._catalog.get_quantity_modifier('shear_2'))
        self._catalog.add_quantity_modifier('kappa', self._catalog.get_quantity_modifier('convergence'))
        self._catalog.add_quantity_modifier('positionAngle', self._catalog.get_quantity_modifier('position_angle'))

        self._catalog.add_quantity_modifier('majorAxis_disk', (arcsec_to_radians, 'morphology/diskMajorAxisArcsec'))
        self._catalog.add_quantity_modifier('minorAxis_disk', (arcsec_to_radians, 'morphology/diskMinorAxisArcsec'))
        self._catalog.add_quantity_modifier('majorAxis_bulge', (arcsec_to_radians, 'morphology/spheroidMajorAxisArcsec'))
        self._catalog.add_quantity_modifier('majorAxis_bulge', (arcsec_to_radians, 'morphology/spheroidMinorAxisArcsec'))

        self._catalog.add_quantity_modifier('sindex_disk', self._catalog.get_quantity_modifier('disk_sersic_index'))
        self._catalog.add_quantity_modifier('sindex_bulge', self._catalog.get_quantity_modifier('bulge_sersic_index'))

        self._make_column_map()

        if self.objectTypeId is None:
            raise RuntimeError("Need to define objectTypeId for your DESCQAObject")

        if self.idColKey is None:
            raise RuntimeError("Need to define idColKey for your DESCQAObject")


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
        self.columnMap = dict()

        if self.columns_need_postfix:
            if not self.postfix:
                raise ValueError('must specify `postfix` when `columns_need_postfix` is not empty')
            for name in self.columns_need_postfix:
                self.columnMap[name] = name + self.postfix


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
        return DESCQAChunkIterator(self._catalog, self.columnMap, obs_metadata,
                                   colnames, None, chunk_size)


class bulgeDESCQAObject(DESCQAObject):
    # PhoSim uniqueIds are generated by taking
    # source catalog uniqueIds, multiplying by
    # 1024, and adding objectTypeId.  This
    # components of the same galaxy to have
    # different uniqueIds, even though they
    # share a uniqueId in the source catalog
    objectTypeId = 77

    # some column names require an additional postfix
    postfix = '_bulge'


class diskDESCQAObject(DESCQAObject):
    objectTypeId = 87
    postfix = '_disk'
