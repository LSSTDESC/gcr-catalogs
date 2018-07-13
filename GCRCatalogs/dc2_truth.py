import os
import numpy as np
import sqlite3
from GCR import BaseGenericCatalog

__all__ = ["DC2TruthCatalogReader"]


class DC2TruthCatalogReader(BaseGenericCatalog):

    native_filter_string_only = True

    def _subclass_init(self, **kwargs):

        if not os.path.isfile(kwargs['filename']):
            raise ValueError("%s is not a valid filename" % kwargs['filename'])

        self._conn = sqlite3.connect(kwargs['filename'])

        # get the descriptions of the columns as provided in the sqlite database
        cursor = self._conn.cursor()
        metadata = cursor.execute('SELECT name, description FROM column_descriptions').fetchall()
        self._column_descriptions = dict(metadata)

        self._quantity_modifiers = {'mag_true_u': 'u',
                                    'mag_true_g': 'g',
                                    'mag_true_r': 'r',
                                    'mag_true_i': 'i',
                                    'mag_true_z': 'z',
                                    'mag_true_y': 'y'}

    def _generate_native_quantity_list(self):
        cursor = self._conn.cursor()
        results = cursor.execute("PRAGMA table_info('truth')").fetchall()
        return [r[1] for r in results]

    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed, native_quantity_getter):
        """
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        return dict(zip(native_quantities_needed, native_quantity_getter(native_quantities_needed)))

    def _iter_native_dataset(self, native_filters=None):
        cursor = self._conn.cursor()

        if native_filters is None:
            query_where_clause = ''
        else:
            query_where_clause = 'WHERE {}'.format(' AND '.join(native_filters))
        
        # define a method to return a native_quantity_getter
        # with the API expected by the GCR
        def dc2_truth_native_quantity_getter(quantities):
            query = 'SELECT {} FROM truth {}'.format(
                ', '.join(quantities),
                query_where_clause
            )
            query_cursor = cursor.execute(query)

            # when we transition to CosmoDC2, this would be a place
            # to use fetchmany(chunk_size) to iterate over manageable
            # chunks of the catalog, if necessary
            return np.array(query_cursor.fetchall()).transpose()

        yield dc2_truth_native_quantity_getter

    def _get_quantity_info_dict(self, quantity, default=None):
        if quantity in self._column_descriptions:
            return {'description': self._column_descriptions[quantity]}
        return default
