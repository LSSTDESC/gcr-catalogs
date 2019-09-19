
# 2019-09-19
# Dominique Boutigny reported that a version of pyarrow 0.12.1
# failed doing the following
# while pyarrow 0.13.0 worked.
# We don't understand why.
import GCRCatalogs
from astropy.table import Table

gc = GCRCatalogs.load_catalog('dc2_object_run2.1i_dr1b')
quantities = ['ra', 'dec']
data = gc.get_quantities(quantities)
# At this point Dominique reports
#
# TypeErrorTraceback (most recent call last)
# <ipython-input-15-9130e233d555> in <module>
#       1 quantities = ['ra', 'dec']
# ----> 2 data = gc.get_quantities(quantities)
# 
# /pbs/throng/lsst/software/desc/anaconda3/lib/python3.7/site-packages/GCR-0.8.8-py3.7.egg/GCR/base.py in get_quantities(self, quantities, filters, native_filters, return_iterator)
#      72 
#      73         data_all = defaultdict(list)
# ---> 74         for data in it:
#      75             for q in quantities:
#      76                 data_all[q].append(data[q])
# 
# /pbs/throng/lsst/software/desc/anaconda3/lib/python3.7/site-packages/GCR-0.8.8-py3.7.egg/GCR/base.py in _get_quantities_iter(self, quantities, filters, native_filters)
#     460         for native_quantity_getter in self._iter_native_dataset(native_filters):
#     461             data = self._load_quantities(quantities.union(set(filters.variable_names)),
# --> 462                                          native_quantity_getter)
#     463             data = filters.filter(data)
#     464             for q in set(data).difference(quantities):
# 
# /pbs/throng/lsst/software/desc/anaconda3/lib/python3.7/site-packages/GCR-0.8.8-py3.7.egg/GCR/base.py in _load_quantities(self, quantities, native_quantity_getter)
#     454     def _load_quantities(self, quantities, native_quantity_getter):
#     455         native_quantities_needed = self._translate_quantities(quantities)
# --> 456         native_data = self._obtain_native_data_dict(native_quantities_needed, native_quantity_getter)
#     457         return {q: self._assemble_quantity(q, native_data) for q in quantities}
#     458 
# 
# /pbs/throng/lsst/software/desc/packages/gcr-catalogs/GCRCatalogs/dc2_dm_catalog.py in _obtain_native_data_dict(native_quantities_needed, native_quantity_getter)
#     280         for multiple columns at once
#     281         """
# --> 282         return native_quantity_getter.read_columns(list(native_quantities_needed), as_dict=True)
#     283 
#     284     def _iter_native_dataset(self, native_filters=None):
# 
# /pbs/throng/lsst/software/desc/packages/gcr-catalogs/GCRCatalogs/dc2_dm_catalog.py in read_columns(self, columns, as_dict)
#     113 
#     114     def read_columns(self, columns, as_dict=False):
# --> 115         d = self.handle.read(columns=columns).to_pandas()
#     116         if as_dict:
#     117             return {c: d[c].values for c in columns}
# 
# /pbs/throng/lsst/software/desc/anaconda3/lib/python3.7/site-packages/pyarrow/array.pxi in pyarrow.lib._PandasConvertible.to_pandas()
# 
# /pbs/throng/lsst/software/desc/anaconda3/lib/python3.7/site-packages/pyarrow/table.pxi in pyarrow.lib.Table._to_pandas()
# 
# /pbs/throng/lsst/software/desc/anaconda3/lib/python3.7/site-packages/pyarrow/pandas_compat.py in table_to_blockmanager(options, table, categories, ignore_metadata)
#     574     block_table = table
#     575 
# --> 576     index_columns_set = frozenset(index_columns)
#     577 
#     578     # 0. 'field_name' is the name of the column in the arrow Table
# 
# TypeError: unhashable type: 'dict'


