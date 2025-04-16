DR_AVAILABLE = False
try:
    from dataregistry import DataRegistry
    from dataregistry.query import Filter
    DR_AVAILABLE = True
    __all__ = ['DR_AVAILABLE', 'DrConfig', 'DrConfigRegister']
except ModuleNotFoundError:
    DR_AVALIABLE = False
    __all__ = ['DR_AVAILABLE']

if DR_AVAILABLE:
    from .base_config import BaseConfigManager, BaseConfig
    from .catalog_helpers import load_yaml_buf
    from .root_dir_manager import RootDirManager

    class DrConfig(BaseConfig):

        def __init__(self, name, dataset_id, manager, resolvers=None,
                     alias_id=None, ref_alias_id=None):
            """
            representation of a config coming from dataregistry

            Parameters:
            name      string
                name as known to user, registered in either
                dataset table or dataset_alias table
            dataset_id int
                dataset_id for this dataset (if an alias, it's the id of
                dataset it refers to or None)
            manager    DrConfigManager object
            resolvers  list of function references with signature
                   `resolver(config_dict, config_name)` returning config dict
            alias_id int
                if not None, this config is an alias and this is
                its id in dataset_alias_table
            ref_alias_id int
                if not None instance is an alias pointing to another alias
                This is the id of the alias it references.
                NOTE:  Might not need this.  BaseConfig.resolve_reference
                       should take care of chained aliases

        """
            super().__init__(name=name, rootname=name)
            self.lower = self.name.lower()  # in case we need it
            self.id = dataset_id
            self._mgr = manager
            self.alias_id = alias_id

            if resolvers:
                self.set_resolvers(*resolvers)

        @property
        def ignore(self):
            return self.name.startswith("_")

        @property
        def _content(self):
            if self._content_ is None:
                if self.id:
                    tbl = "dataset"
                    filters = [Filter(f"{tbl}.{tbl}_id", "==", self.id)]
                    if self._mgr._owner_type:
                        filters.append(Filter(f"{tbl}.owner_type", "==",
                                              self._mgr._owner_type))
                    if self._mgr._owner:
                        filters.append(Filter(f"{tbl}.owner", "==",
                                              self._mgr._owner))
                    d = self._mgr._query.find_datasets(
                        property_names=[f"{tbl}.access_api_configuration"],
                        filters=filters
                    )
                else:
                    tbl = "dataset_alias"
                    filters = [Filter(f"{tbl}.{tbl}_id", "==", self.alias_id)]
                    d = self._mgr._query.find_aliases(
                        property_names=[f"{tbl}.access_api_configuration"],
                        filter=filters
                    )
                self._content_ = load_yaml_buf(
                    d[f"{tbl}.access_api_configuration"][0]
                )

            return self._content_

        # Information kept in a database can't get out of sync the way it
        # can with cloned repos
        def online_alias_check(self):
            pass


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
            dr_reg = DataRegistry(root_dir=dr_root, site=dr_site,
                                  query_mode="production")

            # Find ids, names of all datasets registered with value for access_api
            # set to GCRCatalogs.
            self._query = dr_reg.Query
            properties = ["dataset.name", "dataset.dataset_id", "dataset.status"]
            filters = [Filter("dataset.access_api", "==", "GCRCatalogs")]
            if self._owner_type:
                filters.append(Filter("owner_type", "==", self._owner_type))
            if self._owner:
                filters.append(Filter("owner", "==", self._owner))
            # order_by = ["dataset.name"]
            d = self._query.find_datasets(property_names=properties,
                                          filters=filters)
            #                              order_by=order_by)
            name_set = set(d["dataset.name"])
            names_len = len(d["dataset.name"])
            if names_len > len(name_set):
                raise RuntimeError("Catalog names are not unique")

            for i in range(names_len):
                name = d["dataset.name"][i]
                self._configs[name] = DrConfig(name, d["dataset.dataset_id"][i],
                                               self)

            # Now get aliases
            filters = [Filter("dataset_alias.access_api", "==", "GCRCatalogs")]
            properties = ["dataset_alias.alias", "dataset_alias.dataset_id",
                          "dataset_alias.dataset_alias_id",
                          "dataset_alias.ref_alias_id"]
            d = self._query.find_aliases(property_names=properties,
                                         filters=filters)
            alias_set = set(d["dataset_alias.alias"])
            if alias_set.intersection(name_set):
                raise RuntimeError("Catalog names including aliases are not unique")
            for i in range(len(d["dataset_alias.alias"])):
                name = d["dataset_alias.alias"][i]
                id = d["dataset_alias.dataset_id"][i]
                if id:  # points directly to a dataset
                    self._configs[name] = DrConfig(
                        name, id, self,
                        alias_id=d["dataset_alias.dataset_alias_id"])
                else:  # points to another alias
                    ref_id = d["dataset_alias.ref_alias_id"][i]
                    self._configs[name] = DrConfig(name, None, self,
                                                   ref_alias_id=ref_id)

        def normalize_name(self, name):
            # Currently don't need to do anything to name for data registry
            return name


    class DrConfigRegister(RootDirManager, DrConfigManager):

        def __init__(self, site_config_path=None, user_config_name=None,
                     dr_root=None, dr_schema=None, dr_site=None,
                     owner_type=None, owner=None):
            if dr_schema is None or dr_schema.find("production") > -1:
                owner_type = "production"
                owner = "production"
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
