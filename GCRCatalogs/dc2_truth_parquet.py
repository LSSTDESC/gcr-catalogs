"""
Reader for truth catalogs persisted as parquet files.  May also be
suitable for other catalogs coming from parquet
"""

import os
import re
import warnings

import pyarrow.parquet as pq
import yaml
from GCR import BaseGenericCatalog

from .utils import first

__all__ = ['DC2TruthParquetCatalog']

class ParsePathInfo():
    _group_pat = r'\{[a-zA-Z_][a-zA-Z0-9_]*\}'
    _known_ints = ('tract', 'visit', 'healpix')
    #_path_key = 'PATH'

    def __init__(self, base_template):
        '''
        From base_template generate a regular expression to find files
        included in the catalog.  If base_template includes substrings
        of the form {ID} where ID is a valid identifier, ID will become
        a group name in the re.  If ID is one of a set of known identifiers
        which typically have integer values, the generated pattern 
        will enforce that restriction
        '''
        groups = re.findall(self._group_pat, base_template)
        base_pat = base_template
        self._gnames = []
        for g in groups:
            if len(groups) > len(set(groups)):
                # can't handle duplicates
                warnings.warn(f'Duplicate group name in pattern {base_template} not allowed!')
                return
            gname = g[1:-1]
            self._gnames.append(gname)
            if gname in self._known_ints:
                base_pat = base_pat.replace(g, fr'(?P<{gname}>\d+)')
            else:
                base_pat = base_pat.replace(g, fr'(?P<{gname}>\w+)')            
            
        self.pattern = re.compile(base_pat)

    @property
    def group_names(self):
        """
        Returns a (possibly empty) list of group names from the file pattern
        As far as the reader is considered, anythng in this list may be used as
        a native filter
        """
        return self._gnames

    def file_info(self, path):
        """
        If path matches pattern, return a dict
        * for each named group, add entry to dict with key = group name
          and value = matched string
        * return { } if there are no groups to match

        otherwise (no match) return None
        """
        m = self.pattern.match(path)
        if not m: return None

        d = m.groupdict()
        if d == None : d = {}

        for (k, v) in d.items():
            try:
                castv = int(v)
                d[k] = castv
            except ValueError:
                pass
        return d

#from .dc2_dm_catalog import ParquetFileWrapper
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
    
class DC2TruthParquetCatalog(BaseGenericCatalog):
    r"""
       DC2 Truth (parquet) Catalog reader

       Presents tables exactly as they are defined in the files (no aliases, 
       no derived quantities)

       Parameters
       ----------
       base_dir         (str): Directory of data files being served.  Required.
       filename_pattern (str): Optional "enhanced regex" pattern of served data files.
                               Default is match anything

       If filename_pattern contains substrings like "{some_ident}"  where some_ident
       is a legal identifier, this part of the pattern will be replaced with
       a regex expression for a group matching a string of digits or word characters,
       e.g.  
             (?P<some_ident>\d+) or              (?P<some_ident>\w+)
       The first form will be used iff the identifier is one of a well-known set
       with integer values, currently ('tract', 'visit', 'healpix')

       Such group names may be used subsequently as native_filter_quantities
       If filename_pattern already includes standard regex syntax for named groups,
       those group names may also be used as native filters
    """

    def _subclass_init(self, **kwargs):
        self.base_dir = kwargs['base_dir']
        self.path_parser = ParsePathInfo(kwargs.get('filename_pattern','.*'))

        if not os.path.isdir(self.base_dir):
            raise ValueError('`base_dir` {} is not a valid directory'.format(self.base_dir))
        self._datasets = self._generate_datasets()
        if not self._datasets:
            err_msg = 'No catalogs were found in `base_dir` {}'
            raise RuntimeError(err_msg.format(self.base_dir))

        self._columns = first(self._datasets).columns

        self._quantity_modifiers = {col: None for col in self._columns}
        
        self._schema = self._generate_schema_from_datafiles(self._datasets)
        self._native_filter_quantities = set(self.path_parser.group_names)
   
    def _generate_datasets(self):
        """Return viable data sets from all files in self.base_dir

        Returns:
            A list of  ParquetFileWrapper objects.  If any native filters come from
            filepath re, dict of their values will be stored in the object
        """
        datasets = list()
        for fname in sorted(os.listdir(self.base_dir)):
            info_dict = self.path_parser.file_info(fname)
            if info_dict == None:
                continue
            datasets.append(ParquetFileWrapper(os.path.join(self.base_dir, fname),
                                               info=info_dict))
        return datasets

    @staticmethod
    def _generate_schema_from_datafiles(datasets):
        schema = {}

        for dataset in datasets:
            x = dataset.native_schema
            schema.update(x)

        return schema

    def _generate_native_quantity_list(self):
        return set(self._schema.keys()).union(self._native_filter_quantities)

    @staticmethod
    def _obtain_native_data_dict(native_quantities_needed, native_quantity_getter):
        """
        Overloading this so that we can query the database backend
        for multiple columns at once
        """
        #return native_quantity_getter.read_columns(list(native_quantities_needed), as_dict=True)
        return native_quantity_getter.read_columns_row_group(list(native_quantities_needed), as_dict=True)

    def _iter_native_dataset(self, native_filters=None):
        for dataset in self._datasets:
            if (native_filters is not None and
                    not native_filters.check_scalar(dataset.info)):
                continue
            for i in range(dataset.num_row_groups):
                dataset.row_group = i
                yield dataset


    
