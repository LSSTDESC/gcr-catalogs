import os
import sqlite3
import numpy as np
from GCR import BaseGenericCatalog
from .utils import md5, is_string_like

__all__ = ["DC2TruthCatalogReader"]


class DC2TruthCatalogReader(BaseGenericCatalog):
    """
    DC2 truth catalog reader

    Parameters
    ----------
    filename : str
        path to the sqlite database file
    base_filters : str or list of str, optional
        set of filters to always apply to the where clause
    """

    native_filter_string_only = True

    def _subclass_init(self, **kwargs):
        self._filename = kwargs['filename']
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
        results = cursor.execute('SELECT name, description FROM column_descriptions')
        self._column_descriptions = dict(results.fetchall())

        results = cursor.execute("PRAGMA table_info('truth')")
        self._native_quantity_dtypes = {t[1]: t[2] for t in results.fetchall()}

        self._quantity_modifiers = {
            'mag_true_u': 'u',
            'mag_true_g': 'g',
            'mag_true_r': 'r',
            'mag_true_i': 'i',
            'mag_true_z': 'z',
            'mag_true_y': 'y',
            'agn': (lambda x: x.astype(np.bool)),
            'star': (lambda x: x.astype(np.bool)),
            'sprinkled': (lambda x: x.astype(np.bool)),
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
            query_where_clause = 'WHERE {}'.format(' AND '.join(all_filters))
        else:
            query_where_clause = ''

        def dc2_truth_native_quantity_getter(quantities):
            # note the API of this getter is not normal, and hence
            # we have overwritten _obtain_native_data_dict
            dtype = np.dtype([(q, self._native_quantity_dtypes[q]) for q in quantities])
            query = 'SELECT {} FROM truth {}'.format(
                ', '.join(quantities),
                query_where_clause
            )
            # may need to switch to fetchmany for larger dataset
            return np.array(cursor.execute(query).fetchall(), dtype)

        yield dc2_truth_native_quantity_getter

    def _get_quantity_info_dict(self, quantity, default=None):
        if quantity in self._column_descriptions:
            return {'description': self._column_descriptions[quantity]}
        return default
