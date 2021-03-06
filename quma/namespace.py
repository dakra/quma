from itertools import chain
from pathlib import Path

from .query import (
    CursorQuery,
    Query,
)


def get_namespace(self, attr):
    if attr in self.namespaces:
        return self.namespaces[attr]

    root = self.namespaces['__root__']
    while root:
        try:
            return getattr(root, attr)
        except AttributeError:
            root = root.shadow
    raise AttributeError


class Namespace(object):
    def __init__(self, db, sqldir, shadow=None):
        self.db = db
        self.sqldir = sqldir
        self.cache = db.cache
        self.show = db.show
        self.shadow = shadow
        self._queries = {}
        if db.cache:
            self._collect_queries(sqldir)

    def _collect_queries(self, sqldir):
        sqlfiles = chain(sqldir.glob('*.{}'.format(self.db.file_ext)),
                         sqldir.glob('*.{}'.format(self.db.tmpl_ext)))

        for sqlfile in sqlfiles:
            filename = Path(sqlfile.name)
            attr = filename.stem
            ext = filename.suffix

            if hasattr(self, attr):
                # We have real namespace method which shadows
                # this file
                attr = '_' + attr

            with open(str(sqlfile), 'r') as f:
                self._queries[attr] = self.db.query_factory(
                    f.read(),
                    self.show,
                    ext.lower() == '.' + self.db.tmpl_ext,
                    prepare_params=self.db.prepare_params)

    def __getattr__(self, attr):
        if self.cache:
            try:
                return self._queries[attr]
            except KeyError:
                return getattr(self.shadow, attr)

        try:
            sqlfile = self.sqldir / '.'.join((attr, self.db.file_ext))
            if not sqlfile.is_file():
                sqlfile = self.sqldir / '.'.join((attr, self.db.tmpl_ext))
            with open(str(sqlfile), 'r') as f:
                return self.db.query_factory(
                    f.read(),
                    self.show,
                    Path(sqlfile).suffix == '.' + self.db.tmpl_ext,
                    prepare_params=self.db.prepare_params)
        except FileNotFoundError:
            return getattr(self.shadow, attr)


class CursorNamespace(object):
    def __init__(self, namespace, cursor):
        self.namespace = namespace
        self.cursor = cursor

    def __getattr__(self, attr):
        if type(self.namespace) is Query:
            return getattr(CursorQuery(self.namespace, self.cursor), attr)
        attr_obj = getattr(self.namespace, attr)
        if type(attr_obj) is Query:
            return CursorQuery(attr_obj, self.cursor)
        return attr_obj

    def __call__(self, *args, **kwargs):
        if type(self.namespace) is Query:
            return self.namespace(self.cursor, *args, **kwargs)
        # Should be a custom namespace method
        return self.namespace(*args, **kwargs)
