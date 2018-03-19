from . import exc


class Connection(object):
    def __init__(self, url, **kwargs):
        self.database = url.path[1:]  # remove the leading slash
        self.username = url.username
        self.password = url.password
        self.url = url

        self.factory = None
        self.persist = kwargs.pop('persist', False)
        self.changeling = kwargs.pop('changeling', False)
        self.has_rowcount = True

    def _init_conn(self, **kwargs):
        if self.persist:
            self.conn = self.get()

    def cursor(self, conn):
        return conn.cursor()

    def create_conn(self):
        raise NotImplementedError

    def get(self):
        return getattr(self, 'conn', self.create_conn())

    def put(self, conn):
        if not self.persist:
            conn.close()

    def close(self):
        if not self.persist:
            raise exc.APIError("Don't call the close() method of "
                               "non-persistent connections.")
        if self.conn:
            self.conn.close()
            del self.conn
