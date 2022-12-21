"""
Reference Catalog Reader
"""
import os
import numpy as np
from GCR import BaseGenericCatalog

__all__ = ['ReferenceCatalogReader']

class ReferenceCatalogReader(BaseGenericCatalog):
    """
    Reference Catalog Reader

    Parameters
    ----------
    filename : str
    nlines : None or int, optional (default: 10000)
        how many lines to read at once
    max_chunks : None or int, optional (default: None)
        how many chunks to read.
        Set to 1 if you just want to test the reader.
        Set to None to read all chunks.
    """

    def _subclass_init(self, **kwargs):
        self._filename = kwargs['filename']
        if not os.path.isfile(self._filename):
            raise ValueError('File {} not found'.format(self._filename))

        self._nlines = kwargs.get('nlines', 10000)
        self._nlines = None if self._nlines is None else int(self._nlines)

        self._max_chunks = kwargs.get('max_chunks')
        self._max_chunks = None if self._max_chunks is None else int(self._max_chunks)

        self._quantity_modifiers = {
            'object_id': 'uniqueId',
            'ra' : 'raJ2000_smeared',
            'dec' : 'decJ2000_smeared',
            'ra_unsmeared' : 'raJ2000',
            'dec_unsmeared' : 'decJ2000',
            'sigma_ra' : 'sigma_raJ2000',
            'sigma_dec' : 'sigma_decJ2000',
            'is_agn': (lambda x: x.astype(bool), 'isagn'),
            'is_resolved': (lambda x: x.astype(bool), 'isresolved'),
        }

        for band in 'ugrizy':
            self._quantity_modifiers['mag_{}_unsmeared'.format(band)] = 'lsst_{}'.format(band)
            self._quantity_modifiers['mag_{}'.format(band)] = 'lsst_{}_smeared'.format(band)
            self._quantity_modifiers['mag_{}_lsst'.format(band)] = 'lsst_{}_smeared'.format(band)

        self._header_line_number = 0
        self._data_dtype = None


    def _iter_native_dataset(self, native_filters=None):
        if native_filters is not None:
            raise ValueError('`native_filter` not supported!')

        with open(self._filename, 'rb') as f:
            for _ in range(self._header_line_number):
                next(f, None)

            chunk_count = 0
            while self._max_chunks is None or chunk_count < self._max_chunks:
                data = np.genfromtxt(f, self._data_dtype, delimiter=',', max_rows=self._nlines)
                if len(data) == 0:
                    break
                yield data.__getitem__
                chunk_count += 1


    def _generate_native_quantity_list(self):
        line = None
        with open(self._filename, 'r') as f:
            for i, line in enumerate(f):
                if line.startswith('#') and 'uniqueId' in line:
                    self._header_line_number = i + 1
                    break #found the header line!

        if not line:
            raise ValueError('Cannot find header line!')

        fields = [field.strip() for field in line[1:].split(',')]
        self._data_dtype = np.dtype([(field, int if field.startswith('is') or field.endswith('Id') else float) for field in fields])
        return fields
