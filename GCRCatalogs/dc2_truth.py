import os
import numpy as np
import sqlite3
from GCR import BaseGenericCatalog

__all__ = ["DC2TruthCatalogReader"]


class DC2TruthCatalogReader(BaseGenericCatalog):

    def _subclass_init(self, **kwargs):

        self._allow_string_native_filter = True

        if not os.path.isfile(kwargs['filename']):
            raise ValueError("%s is not a valid filename" % kwargs['filename'])

        self._conn = sqlite3.connect(kwargs['filename'])

        # get the descriptions of the columns as provided in the sqlite database
        cursor = self._conn.cursor()
        metadata = cursor.execute('SELECT name, description FROM column_descriptions').fetchall()
        self._column_descriptions = {}
        for mm in metadata:
            self._column_descriptions[mm[0]] = mm[1]

    def _generate_native_quantity_list(self):
        cursor = self._conn.cursor()
        results = cursor.execute("PRAGMA table_info('truth')").fetchall()
        return [r[1] for r in results]

    def _iter_native_dataset(self, native_filters=None):
        cursor = self._conn.cursor()

        column_list = list(self._native_quantities)
        query = 'SELECT '
        for column_name in column_list:
            if query != 'SELECT ':
                query += ', '
            query += column_name

        query += ' FROM truth'

        if native_filters is not None:
            query += ' WHERE'

            if not isinstance(native_filters, list) and not isinstance(native_filters, tuple):
                native_filters = [native_filters]

            for i_filt, filt in enumerate(native_filters):
                if i_filt > 0:
                    query += ' AND'
                query += ' {}'.format(filt)

        query_cursor = cursor.execute(query)

        # when we transition to CosmoDC2, this would be a place
        # to use fetchmany(chunk_size) to iterate over manageable
        # chunks of the catalog, if necessary
        query_result = np.array(query_cursor.fetchall()).transpose()

        out_dict = {}
        for i_col, column_name in enumerate(column_list):
            out_dict[column_name] = query_result[i_col]

        # define a method to return a native_quantity_getter
        # with the API expected by the GCR
        def dc2_truth_native_quantity_getter(quantity):
            return out_dict[quantity]

        yield dc2_truth_native_quantity_getter

    def _get_quantity_info_dict(self, quantity, default=None):
        if quantity in self._column_descriptions:
            return {'description:' self._column_descriptions[quantity]}
        return default
