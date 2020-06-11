import pyarrow.parquet as pq
import re

__all__ = ['ParquetFileWrapper']

class ParquetFileWrapper():
    def __init__(self, file_path, info=None):
        self.path = file_path
        self._handle = None
        self._columns = None
        self._info = info or dict()
        self._schema = None
        self._row_group = 0

    @property
    def handle(self):
        if self._handle is None:
            self._handle = pq.ParquetFile(self.path)
        return self._handle

    @property
    def num_row_groups(self):
        return self.handle.metadata.num_row_groups

    @property
    def row_group(self):
        return self._row_group

    @row_group.setter
    def row_group(self, grp):
        self._row_group = grp

    def close(self):
        self._handle = None

    def __len__(self):
        return int(self.handle.scan_contents)

    def __contains__(self, item):
        return item in self.columns

    def read_columns(self, columns, as_dict=False):
        d = self.handle.read(columns=columns).to_pandas()
        if as_dict:
            return {c: d[c].values for c in columns}
        return d

    def read_columns_row_group(self, columns, as_dict=False):
        d = self.handle.read_row_group(self._row_group, columns=columns).to_pandas()
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

    @property
    def native_schema(self):
        if self._schema is None:
            self._schema = {}
            arrow_schema = self.handle.schema.to_arrow_schema()
            for i in range(len(arrow_schema.names)):
                tp = str(arrow_schema[i].type)
                if tp == 'float': tp = 'float32'
                else:
                    if tp == 'double': tp = 'float42'
                self._schema[arrow_schema.names[i]] = {'dtype' : tp}
        
        return self._schema
