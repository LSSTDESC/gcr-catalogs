import re
import warnings

__all__ = ['PathInfoParser']

class PathInfoParser():
    _group_pat = r'\{[a-zA-Z_][a-zA-Z0-9_]*\}'
    _known_ints = ('tract', 'visit', 'healpix')

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

        d = m.groupdict() or {}

        for (k, v) in d.items():
            try:
                castv = int(v)
            except ValueError:
                pass
            else:
                d[k] = castv
        return d
