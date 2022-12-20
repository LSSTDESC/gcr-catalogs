"""
Reader for truth catalogs persisted as parquet files.  May also be
suitable for other catalogs coming from parquet
"""

import os

from GCR import BaseGenericCatalog

from .parquet import ParquetFileWrapper
from .parse_utils import PathInfoParser
from .utils import first

__all__ = ['DC2TruthParquetCatalog']


class DC2TruthParquetCatalog(BaseGenericCatalog):
    r"""
       DC2 Truth (parquet) Catalog reader

       Presents tables exactly as they are defined in the files (no aliases,
       no derived quantities)

       Parameters
       ----------
       base_dir         (str): Directory of data files being served.  Required.
       filename_pattern (str): Optional "enhanced regex" pattern of served data
                               files.
                               Default is match anything

       If filename_pattern contains substrings like "{some_ident}"  where
       some_ident is a legal identifier, this part of the pattern will be
       replaced with a regex expression for a group matching a string of
       digits or word characters,
       e.g.
             (?P<some_ident>\d+) or              (?P<some_ident>\w+)
       The first form will be used iff the identifier is one of a well-known set
       with integer values, currently ('tract', 'visit', 'healpix')

       Such group names may be used subsequently as native_filter_quantities
       If filename_pattern already includes standard regex syntax for named
       groups, those group names may also be used as native filters
    """

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self.path_parser = PathInfoParser(kwargs.get('filename_pattern', '.*'))

        if not os.path.isdir(self.base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self.base_dir))
        self._datasets = self._generate_datasets()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self.base_dir))

        self._columns = first(self._datasets).columns

        self._quantity_modifiers = {col: None for col in self._columns}

        self._native_filter_quantities = set(self.path_parser.group_names)
        self._len = None

    def _generate_datasets(self):
        """Return viable data sets from all files in self.base_dir

        Returns:
            A list of  ParquetFileWrapper objects.  If any native filters come
            from filepath re, dict of their values will be stored in the object
        """
        datasets = list()
        for fname in sorted(os.listdir(self.base_dir)):
            info_dict = self.path_parser.file_info(fname)
            if info_dict is None:
                continue
            datasets.append(ParquetFileWrapper(os.path.join(self.base_dir,
                                                            fname),
                                               info=info_dict))
        return datasets

    def _generate_native_quantity_list(self):
        return self._columns

    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed,
                                 native_quantity_getter):
        """
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        return native_quantity_getter.read_columns_row_group(list(native_quantities_needed), as_dict=True)

    def __len__(self):
        if self._len is None:
            self._len = sum(len(dataset) for dataset in self._datasets)
        return self._len

    def _iter_native_dataset(self, native_filters=None):
        for dataset in self._datasets:
            if (native_filters is not None and
                    not native_filters.check_scalar(dataset.info)):
                continue
            for i in range(dataset.num_row_groups):
                dataset.current_row_group = i
                yield dataset

    def close_all_file_handles(self):
        """Clear all cached file handles"""
        for dataset in self._datasets:
            dataset.close()
