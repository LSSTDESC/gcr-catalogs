import pyarrow.parquet as pq
import re

__all__ = ['ParquetFileWrapper']

class ParquetFileWrapper():
    '''
    Provide services commonly needed when catalog consists of one or more parquet files.
    Typical usage by a GCR reader might include
        creating a ParquetFileWrapper object for each parquet file in _generate_datasets
        ParquetFileWrapper object will serve as native_quantity_getter in reader's
            implementation of _obtain_native_data_dict
        Yield instance of ParquetFileObject in implementation of _iter_native_dataset

    There are two ways to read data using a ParquetFileWrapper object: either read data
    a file at a time (use read_columns) or a row group at a time (use read_columns_row_group).
    In the latter case _iter_native_dataset will have to iterate over row groups as well
    as files.  See reader dc2_truth_parquet.py for an example.
    The two methods are equivalent for files having only a single row group.
        
    '''
    def __init__(self, file_path, info=None):
        '''
        Parameters
        ----------
        file_path    string   Full path to underlying parquet file (required)
        info         dict     Associate native filter names with values for this file (optional)
        '''
        self.path = file_path
        self._handle = None
        self._columns = None
        self._info = info or dict()
        self._row_group = 0  # store the current row group index

    @property
    def handle(self):
        if self._handle is None:
            self._handle = pq.ParquetFile(self.path)
        return self._handle

    @property
    def num_row_groups(self):
        return self.handle.metadata.num_row_groups

    @property
    def current_row_group(self):
        return self._row_group

    @current_row_group.setter
    def current_row_group(self, grp):
        self._row_group = int(grp)

    def close(self):
        self._handle = None

    def __len__(self):
        return int(self.handle.scan_contents)

    def __contains__(self, item):
        return item in self.columns

    def read_columns(self, columns, as_dict=False):
        '''
        Read all values for specified columns

        Parameters
        ----------
        columns   list of columns to be read
        as_dict   boolean.  If true, return data as dict where keys are column names
                            Else return pandas dataframe 
        returns
        -------
        dict or dataframe   See as_dict parameter above

        '''
        d = self.handle.read(columns=columns).to_pandas()
        if as_dict:
            return {c: d[c].values for c in columns}
        return d

    def read_columns_row_group(self, columns, as_dict=False):
        '''
        Read specified columns for a single row group, the one stored in the property
        current_row_group

        Parameters
        ----------
        columns   list of columns to be read
        as_dict   boolean.  If true, return data as dict where keys are column names
                            Else return pandas dataframe 
        returns
        -------
        dict or dataframe   See as_dict parameter above
        '''
        d = self.handle.read_row_group(self.current_row_group, columns=columns).to_pandas()
        if as_dict:
            return {c: d[c].values for c in columns}
        return d
        

    @property
    def info(self):
        return dict(self._info)

    def __getattr__(self, name):
        if name not in self._info:
            raise AttributeError('Attribute {} does not exist'.format(name))
        return self._info[name]

    @property
    def columns(self):
        if self._columns is None:
            self._columns = [col for col in self.handle.schema.to_arrow_schema().names
                             if re.match(r'__\w+__$', col) is None]
        return list(self._columns)
