import os
import numpy as np
import sqlite3
from GCR import BaseGenericCatalog

__all__ = ["DC2TruthCatalogReader"]


class DC2TruthCatalogReader(BaseGenericCatalog):

    def _subclass_init(self, **kwargs):
        if not os.path.isfile(kwargs['filename']):
            raise ValueError("%s is not a valid filename" % kwargs['filename'])

        self._conn = sqlite3.connect(kwargs['filename'])

    def _generate_native_quantity_list(self):
        cursor = self._conn.cursor()
        results = cursor.execute("PRAGMA table_info('truth')").fetchall()
        return [r[1] for r in results]
