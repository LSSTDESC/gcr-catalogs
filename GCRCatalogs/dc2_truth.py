import os
import warnings
import sqlite3
import numpy as np
import h5py
from GCR import BaseGenericCatalog
from .utils import md5, is_string_like

__all__ = ['DC2TruthCatalogReader', 'DC2TruthCatalogLightCurveReader',
           'DC2TruthLCSummaryReader']


class DC2TruthLCSummaryReader(BaseGenericCatalog):
    """
    Reader for hdf5 file containing summary information for variables and
    transients in DC2

    Parameters
    ----------
    filename: str
        path to the hdf5 file containing the summary catalog
    """

    def _subclass_init(self, **kwargs):
        self._file_name = kwargs['filename']

        self._info_dict = {}
        self._info_dict['redshift'] = {'units': 'unitless'}
        self._info_dict['ra'] = {'units': 'degrees'}
        self._info_dict['dec'] = {'units': 'degrees'}
        self._info_dict['uniqueId'] = {'units': 'unitless',
                     'description': 'an int uniquely identifying the object. '
                     'Does NOT correspond to galaxy_id in the extra-galactic '
                     'catalog.'}

        self._info_dict['galaxy_id'] = {'units': 'unitless',
                       'description':
                       'should correspond to galaxy_id in the extra-galactic '
                       'catalog.  Note: sprinkled objects and all supernovae '
                       'will not have sensible values of galaxy_id.'}

        self._info_dict['agn'] = {'units': 'unitless',
                    'description': 'an int that is 1 for AGN and 0 for '
                    'all other objects.'}

        self._info_dict['sn'] = {'units': 'unitless',
                  'description': 'an int that is 1 for supernovae and 0 for '
                  'all other objects'}

        self._info_dict['sprinkled'] = {'units': 'unitless',
                   'description': 'an int that is 1 if the object was '
                   'added by the sprinkler; 0 otherwise.'}

    def _get_quantity_info(self, quantity, default=None):
        return self._info_dict.get(quantity, default)

    def _generate_native_quantity_list(self):
        with h5py.File(self._file_name, 'r') as file_handle:
            return list(file_handle.keys())

    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            warnings.warn("Native filters are not implemented "
                          "for this catalog; just use filters.")
        with h5py.File(self._file_name, 'r') as file_handle:
            def _native_qty_getter(qty_name):
                return file_handle[qty_name][()]
            yield _native_qty_getter

    def get_quantities(self, quantities, filters=None, native_filters=None, return_iterator=False):
        if native_filters is not None:
            warnings.warn('For this particular truth catalog, `native_filters` is no longer supported.\n'
                'Please use `filters` instead. For now this code will include your `native_filters` in `filters`.\n'
                '(Note that `native_filters` still works for other GCR catalogs.)')
            filters = self._preprocess_filters(native_filters) & self._preprocess_filters(filters)
            native_filters = None

        return super().get_quantities(quantities, filters, native_filters, return_iterator)


class DC2TruthCatalogReader(BaseGenericCatalog):
    """
    DC2 truth catalog reader

    Parameters
    ----------
    filename : str
        path to the sqlite database file
    table_name : str
        table name
    is_static : bool
        whether or not this is for static objects only
    base_filters : str or list of str, optional
        set of filters to always apply to the where clause
    """

    native_filter_string_only = True

    def _subclass_init(self, **kwargs):
        self._filename = kwargs['filename']

        self._table_name = kwargs.get('table_name', 'truth')
        self._is_static = kwargs.get('is_static', True)

        base_filters = kwargs.get('base_filters')
        if base_filters:
            if is_string_like(base_filters):
                self.base_filters = (base_filters,)
            else:
                self.base_filters = tuple(base_filters)
        else:
            self.base_filters = tuple()

        if not os.path.isfile(self._filename):
            raise ValueError('{} is not a valid file'.format(self._filename))

        if kwargs.get('md5') and md5(self._filename) != kwargs['md5']:
            raise ValueError('md5 sum does not match!')

        self._conn = sqlite3.connect(self._filename)

        # get the descriptions of the columns as provided in the sqlite database
        cursor = self._conn.cursor()
        if self._is_static:
            results = cursor.execute('SELECT name, description FROM column_descriptions;')
            self._column_descriptions = dict(results.fetchall())
        else:
            self._column_descriptions = dict()

        results = cursor.execute('PRAGMA table_info({});'.format(self._table_name))
        self._native_quantity_dtypes = {t[1]: t[2] for t in results.fetchall()}

        if self._is_static:
            self._quantity_modifiers = {
                'mag_true_u': 'u',
                'mag_true_g': 'g',
                'mag_true_r': 'r',
                'mag_true_i': 'i',
                'mag_true_z': 'z',
                'mag_true_y': 'y',
                'agn': (lambda x: x.astype(bool)),
                'star': (lambda x: x.astype(bool)),
                'sprinkled': (lambda x: x.astype(bool)),
            }

    def _generate_native_quantity_list(self):
        return list(self._native_quantity_dtypes)

    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed, native_quantity_getter):
        """
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        return native_quantity_getter(native_quantities_needed)

    def _iter_native_dataset(self, native_filters=None):
        cursor = self._conn.cursor()

        if native_filters is not None:
            all_filters = self.base_filters + tuple(native_filters)
        else:
            all_filters = self.base_filters

        if all_filters:
            query_where_clause = 'WHERE ({})'.format(') AND ('.join(all_filters))
        else:
            query_where_clause = ''

        def dc2_truth_native_quantity_getter(quantities):
            # note the API of this getter is not normal, and hence
            # we have overwritten _obtain_native_data_dict
            dtype = np.dtype([(q, self._native_quantity_dtypes[q]) for q in quantities])
            query = 'SELECT {} FROM {} {};'.format(
                ', '.join(quantities),
                self._table_name,
                query_where_clause
            )
            # may need to switch to fetchmany for larger dataset
            return np.array(cursor.execute(query).fetchall(), dtype)

        yield dc2_truth_native_quantity_getter

    def _get_quantity_info_dict(self, quantity, default=None):
        if quantity in self._column_descriptions:
            return {'description': self._column_descriptions[quantity]}
        return default


class DC2TruthCatalogLightCurveReader(BaseGenericCatalog):
    """
    DC2 truth catalog reader for light curves

    Parameters
    ----------
    filename : str
        path to the sqlite database file
    table_light_curves : str
        light curve table name
    table_summary : str
        summary table name
    table_obs_metadata : str
        observation metadata table name
    base_filters : str or list of str, optional
        set of filters to always apply to the where clause
    """

    native_filter_string_only = True

    def _subclass_init(self, **kwargs):
        self._filename = kwargs['filename']

        self._tables = dict()
        self._tables['light_curves'] = kwargs.get('table_light_curves', 'light_curves')
        self._tables['summary'] = kwargs.get('table_summary', 'variables_and_transients')
        self._tables['obs_meta'] = kwargs.get('table_obs_metadata', 'obs_metadata')

        base_filters = kwargs.get('base_filters')
        if base_filters:
            if is_string_like(base_filters):
                self.base_filters = (base_filters,)
            else:
                self.base_filters = tuple(base_filters)
        else:
            self.base_filters = tuple()

        if not os.path.isfile(self._filename):
            raise ValueError('{} is not a valid file'.format(self._filename))

        if kwargs.get('md5') and md5(self._filename) != kwargs['md5']:
            raise ValueError('md5 sum does not match!')

        self._conn = sqlite3.connect(self._filename)
        cursor = self._conn.cursor()
        self._dtypes = dict()
        for table, table_name in self._tables.items():
            results = cursor.execute('PRAGMA table_info({});'.format(table_name))
            self._dtypes[table] = {t[1]: t[2] for t in results.fetchall()}
        self._dtypes['light_curves'].update(self._dtypes['obs_meta'])
        del self._dtypes['obs_meta']

    def _generate_native_quantity_list(self):
        return list(self._dtypes['light_curves'])

    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed, native_quantity_getter):
        """
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        return native_quantity_getter(native_quantities_needed)

    def _iter_native_dataset(self, native_filters=None):
        cursor = self._conn.cursor()

        if native_filters is not None:
            all_filters = self.base_filters + tuple(native_filters)
        else:
            all_filters = self.base_filters

        if all_filters:
            query_where_clause = 'WHERE ({})'.format(') AND ('.join(all_filters))
        else:
            query_where_clause = ''

        id_col_name = 'uniqueId'
        dtype = np.dtype([(id_col_name, self._dtypes['summary'][id_col_name])])
        query = 'SELECT DISTINCT {} FROM {} {};'.format(
            id_col_name,
            self._tables['summary'],
            query_where_clause
        )
        ids_needed = np.array(cursor.execute(query).fetchall(), dtype)[id_col_name]

        for id_this in ids_needed:
            def dc2_truth_light_curve_native_quantity_getter(quantities):
                # When 'obshistid' is needed, change it to 'obs_meta.obshistid'
                # so that the SQL query would work
                quantities_str = ', '.join((
                    (self._tables['obs_meta'] + '.obshistid') if q == 'obshistid'
                    else q for q in quantities
                ))
                dtype = np.dtype([(q, self._dtypes['light_curves'][q]) for q in quantities])
                query = 'SELECT {0} FROM {1} JOIN {2} ON {1}.{4}={5} AND {1}.{3}={2}.{3};'.format(
                    quantities_str,
                    self._tables['light_curves'],
                    self._tables['obs_meta'],
                    'obshistid',
                    id_col_name,
                    id_this # pylint: disable=cell-var-from-loop
                )
                return np.array(cursor.execute(query).fetchall(), dtype)
            yield dc2_truth_light_curve_native_quantity_getter
