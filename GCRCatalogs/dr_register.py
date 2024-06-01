# import os
# import warnings                       # might not need
# import copy
from .base_config import BaseConfigManager, BaseConfig
from .catalog_helpers import load_yaml_buf
from .root_dir_manager import RootDirManager
from dataregistry import DataRegistry
from dataregistry.query import Filter


class DrConfig(BaseConfig):

    def __init__(self, name, dataset_id, manager, resolvers=None,
                 aliased_to=None):
        """
        representation of a config coming from dataregistry

        Parameters:
        name      string     name as known to user, registered in either
                             dataset table or dataset_alias table
        dataset_id int       dataset_id for this dataset (if an alias,
                             it's the id of dataset it refers to)
        manager    DrConfigManager object
        resolvers  list of function references with signature
                   `resolver(config_dit, config_name)` returning config dict
        aliased_to int    if not None, name is actually an alias name,
                          aliased to something in the dataset table.
                          aliased_to is that row's dataset_id
                          NOTE: also need to handle case of alias pointing
                                to another alias
        """
        self.name = name
        self.rootname = name
        self.lower = self.name.lower()  # in case we need it
        self.id = dataset_id
        self._mgr = manager
        self.aliased_to = aliased_to

        self._resolvers = None
        self._content_ = None
        self._resolved_content_ = None

        if resolvers:
            self.set_resolvers(*resolvers)

    @property
    def ignore(self):
        return self.name.startswith("_")

    @property
    def _content(self):
        if self._content_ is None:
            # Fetch config content from db
            filters = [Filter("dataset.dataset_id", "==", self.id)]
            if self._mgr._owner_type:
                filters.append(Filter("dataset.owner_type", "==",
                                      self._mgr._owner_type))
            if self._mgr._owner:
                filters.append(Filter("dataset.owner", "==", self._mgr._owner))
            d = self._mgr._query.find_datasets(property_names=["dataset.access_api_configuration"],
                                                  filters=filters)
            self._content_ = load_yaml_buf(d["dataset.access_api_configuration"][0])
        return self._content_

    def online_alias_check(self):
        if not self.is_alias:
            return
        # Not clear what to do here.  Can we get out of sync as can happen
        # with local GCRCatalogs installation?


class DrConfigManager(BaseConfigManager):
    '''
    Analog of ConfigManager when configs are stored in the Data Registry
    '''
    _ACCESS_API = "GCRCatalogs"
    def __init__(self, dr_root=None, dr_schema=None,
                 dr_site=None, owner_type=None, owner=None):
        super().__init__()

        self._owner_type = owner_type
        self._owner = owner
        dr_reg = DataRegistry(schema=dr_schema, root_dir=dr_root, site=dr_site)

        # Find ids, names of all datasets registered with value for access_api
        # set to GCRCatalogs.
        self._query = dr_reg.Query
        properties = ["dataset.name", "dataset.dataset_id", "dataset.status"]
        filters = [Filter("dataset.access_api", "==", "GCRCatalogs")]
        if self._owner_type:
            filters.append(Filter("owner_type", "==", self._owner_type))
        if self._owner:
            filters.append(Filter("owner", "==", self._owner))
        order_by = ["dataset.name"]
        d = self._query.find_datasets(property_names=properties,
                                      filters=filters,
                                      order_by=order_by)
        name_set = set(d['dataset.name'])
        names_len = len(d['dataset.name'])
        if names_len > len(name_set):
            raise RuntimeError("Catalog names are not unique")

        # Also find all aliases which refer to GCRCatalogs
        # datasets and save.

        # Make a dict with values of type DrConfig.  They will initially
        # have content set to None.  May want to cut on value of status

        for i in range(names_len):
            name = d['dataset.name'][i]
            self._configs[name] = DrConfig(name, d['dataset.dataset_id'][i],
                                           self)


class DrConfigRegister(RootDirManager, DrConfigManager):

    def __init__(self, site_config_path=None, user_config_name=None,
                 dr_root=None, dr_schema=None, dr_site=None,
                 owner_type="production", owner="production"):
        DrConfigManager.__init__(self, dr_root=dr_root, dr_schema=dr_schema,
                                 dr_site=dr_site, owner_type=owner_type,
                                 owner=owner)
        RootDirManager.__init__(self, site_config_path, user_config_name)
        for config in self.configs:
            config.set_resolvers(self.resolve_reference, self.resolve_root_dir)

    @property
    def root_dir(self):
        return super().root_dir

    @root_dir.setter
    def root_dir(self, path):
        for config in self._configs:
            config.reset_resolved_content()
        RootDirManager.root_dir.__set__(self, path)  # pylint: disable=no-member

    def retrieve_paths(self, **kwargs):
        kwargs["names_only"] = False
        kwargs["content_only"] = False
        kwargs["resolve_content"] = False
        record = list()
        for config_name, config_dict in self.get_configs(**kwargs).items():
            self.resolve_root_dir(config_dict, config_name, record)
        return record
