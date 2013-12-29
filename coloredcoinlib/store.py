""" sqlite3 implementation of storage for color data """

import sqlite3

from UserDict import DictMixin
import cPickle as pickle


class DataStoreConnection(object):
    """ A database connection """
    def __init__(self, path, autocommit=False):
        self.path = path
        self.conn = sqlite3.connect(path)
        if autocommit:
            self.conn.isolation_level = None

    def __del__(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()


class DataStore(object):
    """ Represents a database and allows it's
    manipulation via queries."""
    def __init__(self, conn):
        self.conn = conn

    def table_exists(self, table_name):
        res = self.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name, )).fetchone()
        return res is not None

    def execute(self, statement, params=()):
        cur = self.conn.cursor()
        cur.execute(statement, params)
        return cur

    def sync(self):
        self.conn.commit()

    def transaction(self):
        return self.conn


def unwrap1(val):
    if val:
        return val[0]
    else:
        return None


class ColorDataStore(DataStore):
    """ A DataStore for color data storage. """
    def __init__(self, conn, tablename='colordata'):
        super(ColorDataStore, self).__init__(conn)
        self.tablename = tablename
        if not self.table_exists(tablename):
            statement = "CREATE TABLE {0} (color_id INTEGER, txhash TEXT, " \
                "outindex INTEGER, value REAL, label TEXT);".format(tablename)
            self.execute(statement)
            statement = "CREATE UNIQUE INDEX {0}_data_idx on {0}(color_id, " \
                "txhash, outindex)".format(tablename)
            self.execute(statement)
        self.queries = dict()
        self.queries['add'] = "INSERT OR REPLACE INTO {0} VALUES " \
            "(?, ?, ?, ?, ?)".format(self.tablename)
        self.queries['remove'] = "DELETE FROM {0} WHERE color_id = ? " \
            "AND txhash = ? AND outindex = ?".format(self.tablename)
        self.queries['get'] = "SELECT value, label FROM {0} WHERE " \
            "color_id = ? AND txhash = ? AND outindex = ?".format(
                self.tablename)
        self.queries['get_any'] = "SELECT color_id, value, label FROM " \
            "{0} WHERE txhash = ? AND outindex = ?".format(self.tablename)
        self.queries['get_all'] = "SELECT txhash, outindex, value, " \
            "label FROM {0} WHERE color_id = ?".format(self.tablename)

    def add(self, color_id, txhash, outindex, value, label):
        self.execute(
            self.queries['add'], (color_id, txhash, outindex, value, label))

    def remove(self, color_id, txhash, outindex):
        self.execute(self.queries['remove'], (color_id, txhash, outindex))

    def get(self, color_id, txhash, outindex):
        return self.execute(
            self.queries['get'], (color_id, txhash, outindex)).fetchone()

    def get_any(self, txhash, outindex):
        return self.execute(
            self.queries['get_any'], (txhash, outindex)).fetchall()

    def get_all(self, color_id):
        return self.execute(self.queries['get_all'], (color_id,)).fetchall()


class PersistentDictStore(DictMixin, DataStore):
    """ Persistent dict object """

    def __init__(self, conn, dictname):
        super(PersistentDictStore, self).__init__(conn)
        conn.text_factory = str
        self.tablename = dictname + "_dict"
        if not self.table_exists(self.tablename):
            self.execute("CREATE TABLE {0} (key NOT NULL PRIMARY KEY "
                         "UNIQUE, value BLOB)".format(self.tablename))

    def deserialize(self, svalue):
        return pickle.loads(svalue)

    def serialize(self, value):
        return pickle.dumps(value)

    def __getitem__(self, key):
        svalue = self.execute(
            "SELECT value FROM {0} WHERE key = ?".format(self.tablename),
            (key,)).fetchone()
        if svalue:
            return self.deserialize(unwrap1(svalue))
        else:
            raise KeyError()

    def __setitem__(self, key, value):
        self.execute(
            "INSERT OR REPLACE INTO {0} VALUES (?, ?)".format(self.tablename),
            (key, self.serialize(value)))

    def __contains__(self, key):
        svalue = self.execute(
            "SELECT value FROM {0} WHERE key = ?".format(self.tablename),
            (key,)).fetchone()
        return svalue is not None

    def __delitem__(self, key):
        if self.__contains__(key):
            self.execute(
                "DELETE FROM {0} WHERE key = ?".format(self.tablename),
                (key,))
        else:
            raise KeyError()

    def keys(self):
        return map(
            unwrap1,
            self.execute(
                "SELECT key FROM {0}".format(self.tablename)).fetchall())


class ColorMetaStore(DataStore):
    """ A DataStore containing meta-information
    on a coloring scheme, like color ids, how much
    of the blockchain was scanned, etc."""
    def __init__(self, conn):
        super(ColorMetaStore, self).__init__(conn)
        if not self.table_exists('scanned_block'):
            self.execute(
                "CREATE TABLE scanned_block "
                "(color_id INTEGER, blockhash TEXT)")
            self.execute(
                "CREATE UNIQUE INDEX scanned_block_idx "
                "on scanned_block(color_id, blockhash)")
        if not self.table_exists('color_map'):
            self.execute(
                "CREATE TABLE color_map (color_id INTEGER PRIMARY KEY "
                "AUTOINCREMENT, color_desc TEXT)")
            self.execute(
                "CREATE UNIQUE INDEX color_map_idx ON color_map(color_desc)")

    def did_scan(self, color_id, blockhash):
        return unwrap1(
            self.execute(
                "SELECT 1 FROM scanned_block WHERE "
                "color_id = ? AND blockhash = ?",
                (color_id, blockhash)).fetchone())

    def set_as_scanned(self, color_id, blockhash):
        self.execute(
            "INSERT INTO scanned_block (color_id, blockhash) "
            "VALUES (?, ?)",
            (color_id, blockhash))

    def resolve_color_desc(self, color_desc, auto_add):
        q = "SELECT color_id FROM color_map WHERE color_desc = ?"
        res = self.execute(q, (color_desc, )).fetchone()
        if (res is None) and auto_add:
            self.execute(
                "INSERT INTO color_map(color_id, color_desc) VALUES (NULL, ?)",
                (color_desc,))
            self.sync()
            res = self.execute(q, (color_desc, )).fetchone()
        return unwrap1(res)

    def find_color_desc(self, color_id):
        q = "SELECT color_desc FROM color_map WHERE color_id = ?"
        return unwrap1(self.execute(q, (color_id,)).fetchone())
