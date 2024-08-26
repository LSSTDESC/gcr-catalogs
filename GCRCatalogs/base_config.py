from collections.abc import Mapping
import warnings
import copy
from GCR import BaseGenericCatalog
from .utils import is_string_like
from .catalog_helpers import import_subclass

__all__ = ['BaseConfig', 'BaseConfigManager', 'load_catalog_from_config_dict']

_GITHUB_REPO = "LSSTDESC/gcr-catalogs"
_GITHUB_ISSUE_URL = f"https://github.com/{_GITHUB_REPO}/issues"


class BaseConfig(Mapping):
    YAML_EXTENSIONS = (".yaml", ".yml")
    ALIAS_KEY = "alias"
    REFERENCE_KEYS = (ALIAS_KEY, "based_on")
    PSEUDO_KEY = "is_pseudo_entry"
    DEFAULT_LISTING_KEY = "include_in_default_catalog_list"
    READER_KEY = "subclass_name"
    DEPRECATED_KEY = "deprecated"
    ADDON_KEY = "addon_for"
    PUBLIC_RELEASE_KEY = "public_release"

    def __init__(self, name=None, rootname=None):
        self.name = name
        self.rootname = rootname
        self._resolved_content_ = None
        self._resolvers = None
        self._content_ = None

    def set_resolvers(self, *resolvers):
        """
        Each resolver will be called with two arguments:
        `resolver(config_dict, config_name)`
        and it should return a config dictionary
        """
        if not all(map(callable, resolvers)):
            raise ValueError("`resolvers` should be callable.")
        self._resolvers = resolvers
        self.reset_resolved_content()

    @property
    def _content(self):
        raise NotImplementedError("Subclass must implement _content")

    @property
    def _resolved_content(self):
        if self._resolved_content_ is None:
            content = self.content
            if self._resolvers:
                for resolver in self._resolvers:
                    content = resolver(content, self.name)
            if any(map(content.get, self.REFERENCE_KEYS)):
                raise ValueError("Fail to resolve references for config `{}`!".format(self.rootname))
            elif not (content.get(self.READER_KEY) or self.is_pseudo):
                raise ValueError("`{}` is missing in config `{}` and its references!".format(self.READER_KEY, self.rootname))
            self._resolved_content_ = content
        return self._resolved_content_

    def reset_resolved_content(self):
        self._resolved_content_ = None

    @property
    def content(self):
        return copy.deepcopy(self._content)

    @property
    def resolved_content(self):
        return copy.deepcopy(self._resolved_content)

    def __getitem__(self, key):
        return self._content[key]

    def __iter__(self):
        return iter(self._content)

    def __len__(self):
        return len(self._content)

    @property
    def is_valid(self):
        return self.get(self.READER_KEY) or self.is_pseudo or self.has_reference

    @property
    def is_default(self):
        return self.get(self.DEFAULT_LISTING_KEY) and not self.is_deprecated and not self.is_pseudo

    @property
    def is_pseudo(self):
        return self.get(self.PSEUDO_KEY)

    @property
    def is_alias(self):
        return self.get(self.ALIAS_KEY)

    @property
    def is_deprecated(self):
        return self.get(self.DEPRECATED_KEY)

    @property
    def is_addon(self):
        return self.get(self.ADDON_KEY)

    @property
    def is_public_release(self):
        return self.get(self.PUBLIC_RELEASE_KEY)

    @property
    def has_reference(self):
        return any(map(self.get, self.REFERENCE_KEYS))

    # Almost all of this is the same for config-from-file and
    # config-from-db.  Just need to break out a little utility to
    # find and load referred-to config
    def online_alias_check(self):
        raise NotImplementedError("Subclass must implement online_alias_check")

    def load_catalog(self, config_overwrite=None):
        if self.is_pseudo:
            raise RuntimeError(
                """This is a pseudo entry that does not have an associated
                   reader and cannot be loaded."""
                f"""Use GCRCatalogs.get_catalog_config({self.rootname}) to
                    see the content of this config file."""
            )
        if self.is_deprecated:
            deprecation_msg = self[self.DEPRECATED_KEY]
            if is_string_like(deprecation_msg):
                deprecation_msg = deprecation_msg.strip() + "\n"
            else:
                deprecation_msg = ""
            warnings.warn(
                f"""`{self.rootname}` has been deprecated and may be removed
                    in the future.\n{deprecation_msg}"""
                f"""If your analysis requires this specific catalog, please
                    open an issue at {_GITHUB_ISSUE_URL}""",
            )
        self.online_alias_check()
        if config_overwrite:
            if any(map(config_overwrite.get, self.REFERENCE_KEYS)):
                raise ValueError("`config_overwrite` cannot specify " + " or ".join(self.REFERENCE_KEYS))
            config_dict = dict(self._resolved_content, **config_overwrite)
        else:
            config_dict = self._resolved_content
        return load_catalog_from_config_dict(config_dict)


class BaseConfigManager(Mapping):
    '''
    Any subclass is responsible for finding all catalogs in its __init__
    function and storing in  .self._configs, indexed by catalog name.
    '''
    def __init__(self):
        self._configs = dict()

    def normalize_name(self, name):
        name = str(name).lower()
        for extension in BaseConfig.YAML_EXTENSIONS:
            if name.endswith(extension):
                return name[:-len(extension)]
        return name

    def __getitem__(self, key):
        try:
            return self._configs[self.normalize_name(key)]
        except KeyError:
            raise KeyError("Catalog `{}` does not exist.".format(key))

    def __iter__(self):
        return iter(self._configs)

    def __len__(self):
        return len(self._configs)

    @property
    def configs(self):
        return self._configs.values()

    def resolve_reference(self, config_dict, config_name=None, past_refs=None):
        """
        This function is a "resolver" function that is used to resolve
        config files.
        It should be supplied to `BaseConfig.set_resolvers`.

        *config_dict* is the input config dictionary and may be modified
        in-place, and will be returned.

        *config_name* is the input catalog name (str).
        It is used to detect recursive reference, and also to satisty the
        required call signature.

        *past_refs* is an optional argument for this function's internal use
        to detect recursive reference,
        """
        if past_refs is None and config_name is not None:
            past_refs = [config_name]

        for key in BaseConfig.REFERENCE_KEYS:
            if config_dict.get(key):
                base_name = self.normalize_name(config_dict[key])
                base_config_dict = self[base_name].content

                if past_refs is None:
                    past_refs = [base_name]
                elif base_name in past_refs:
                    raise RecursionError("Recursive reference to `{}` in config file `{}`".format(base_name, config_name))
                else:
                    past_refs.append(base_name)

                if key != BaseConfig.ALIAS_KEY:
                    del config_dict[key]
                    base_config_dict.update(config_dict)

                return self.resolve_reference(base_config_dict,
                                              past_refs=past_refs)

        return config_dict

    def get_configs(
        self,
        names_only=False,
        content_only=False,
        resolve_content=False,
        include_default_only=False,
        include_addons=False,
        include_deprecated=False,
        include_pseudo=False,
        include_pseudo_only=False,
        include_public_release=False,
        include_public_release_only=False,
        name_startswith=None,
        name_contains=None,
        additional_conditions=None,
    ):
        if names_only and content_only:
            raise ValueError(
                "Options `names_only` and `content_only` cannot both be set to True."
            )
        elif names_only:
            return_type = list
            get_content = lambda config: config.rootname  # noqa: E731
            if resolve_content:
                raise ValueError(
                    "Options `names_only` and `resolve_content` cannot both be set to True."
                )
        elif content_only:
            return_type = list
            if resolve_content:
                get_content = lambda config: config.resolved_content  # noqa: E731
            else:
                get_content = lambda config: config.content  # noqa: E731
        else:
            return_type = dict
            if resolve_content:
                get_content = lambda config: (config.rootname,
                                              config.resolved_content)  # noqa: E731
            else:
                get_content = lambda config: (config.rootname, config.content)  # noqa: E731

        conditions = list()
        if include_default_only:
            conditions.append(lambda config: config.is_default)
        if not include_addons:
            conditions.append(lambda config: not config.is_addon)
        if not include_deprecated:
            conditions.append(lambda config: not config.is_deprecated)
        if include_pseudo_only:
            conditions.append(lambda config: config.is_pseudo)
        elif not include_pseudo:
            conditions.append(lambda config: not config.is_pseudo)
        if include_public_release_only is True:
            conditions.append(lambda config: config.is_public_release)
        elif include_public_release_only:
            conditions.append(lambda config: config.is_public_release and include_public_release_only in config.is_public_release)
        elif not include_public_release:
            conditions.append(lambda config: not config.is_public_release)
        if name_startswith:
            name_startswith_lower = str(name_startswith).lower()
            conditions.append(lambda config: config.name.startswith(name_startswith_lower))
        if name_contains:
            name_contains_lower = str(name_contains).lower()
            conditions.append(lambda config: name_contains_lower in config.name)
        if additional_conditions:
            conditions.extend(additional_conditions)

        def check_conditions(config):
            return all((condition(config) for condition in conditions))

        return return_type((get_content(v) for v in self.configs if check_conditions(v)))

    @property
    def catalog_configs(self):
        return self.get_configs(resolve_content=True, include_pseudo=False)

    @property
    def default_catalog_configs(self):
        return self.get_configs(resolve_content=True,
                                include_default_only=True,
                                include_pseudo=False)

    @property
    def catalog_list(self):
        return self.get_configs(names_only=True, include_pseudo=False)

    @property
    def default_catalog_list(self):
        return self.get_configs(names_only=True, include_default_only=True,
                                include_pseudo=False)

    @property
    def reader_list(self):
        configs = self.get_configs(content_only=True, resolve_content=True,
                                   include_addons=True,
                                   include_deprecated=True,
                                   include_pseudo=False)
        return list(set((v[BaseConfig.READER_KEY] for v in configs)))


def load_catalog_from_config_dict(catalog_config):
    """
    Loads and returns the catalog specified in *catalog_config*.
    """
    return import_subclass(
        catalog_config[BaseConfig.READER_KEY], __package__, BaseGenericCatalog
    )(**catalog_config)
