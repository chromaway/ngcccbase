import sqlite3

class DataStoreConnection(object):
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.isolation_level = None
        
    def __del__(self):
        if self.conn:
            self.conn.close()
            
     
class DataStore(object):
    def __init__(self, conn):
        self.conn = conn
    def table_exists(self, table_name):
        res = self.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name, )).fetchone()
        return res != None
    def execute(self, statement, params = ()):
        cur = self.conn.cursor()
        cur.execute(statement, params)
        return cur

def unwrap1(val):
    if val:
        return val[0]
    else:
        return None


class ColorDataStore(DataStore):
    def __init__(self, conn, tablename = 'colordata'):
        super(ColorDataStore, self).__init__(conn)
        self.tablename = tablename
        if not self.table_exists(tablename):
            statement = "CREATE TABLE {0} (color_id INTEGER, txhash TEXT, outindex INTEGER, value REAL, label TEXT);".format(tablename)
            self.execute(statement)
            statement = "CREATE UNIQUE INDEX {0}_data_idx on {0}(color_id, txhash, outindex)".format(tablename)
            self.execute(statement)
        self.queries = dict()
        self.queries['add'] = "INSERT OR REPLACE INTO {0} VALUES (?, ?, ?, ?, ?)".format(self.tablename)
        self.queries['remove'] = "DELETE FROM {0} WHERE color_id = ? AND txhash = ? AND outindex = ?".format(self.tablename)
        self.queries['get'] = "SELECT value, label FROM {0} WHERE color_id = ? AND txhash = ? AND outindex = ?".format(self.tablename)
        self.queries['get_any'] = "SELECT color_id, value, label FROM {0} WHERE txhash = ? AND outindex = ?".format(self.tablename)
        self.queries['get_all'] = "SELECT txhash, outindex, value, label FROM {0} WHERE color_id = ?".format(self.tablename)
                                                                                                                             
    def add(self, color_id, txhash, outindex, value, label):
        self.execute(self.queries['add'], (color_id, txhash, outindex, value, label))
    def remove(self, color_id, txhash, outindex):
        self.execute(self.queries['remove'], (color_id, txhash, outindex))
    def get(self, color_id, txhash, outindex):
        return self.execute(self.queries['get'], (color_id, txhash, outindex)).fetchone()
    def get_any(self, txhash, outindex):
        return self.execute(self.queries['get_any'], (txhash, outindex)).fetchall()
    def get_all(self, color_id):
        return self.execute(self.queries['get_all'], (color_id,)).fetchall()

class ColorMetaStore(DataStore):
    def __init__(self, conn):
        super(ColorMetaStore, self).__init__(conn)
        if not self.table_exists('builder_state'):
            self.execute("CREATE TABLE builder_state (color_id INTEGER, height INTEGER)")
            self.execute("CREATE UNIQUE INDEX builder_state_idx on builder_state(color_id)")
        if not self.table_exists('color_map'):
            self.execute("CREATE TABLE color_map (color_id INTEGER PRIMARY KEY AUTOINCREMENT, color_desc TEXT)")
            self.execute("CREATE UNIQUE INDEX color_map_idx ON color_map(color_desc)")
    def get_scan_height(self, color_id):
        return unwrap1(self.execute("SELECT height FROM builder_state WHERE color_id = ?", (color_id, )).fetchone())
    def set_scan_height(self, color_id, height):
        self.execute("INSERT OR REPLACE INTO builder_state VALUES (?, ?)", (color_id, height))
    def resolve_color_desc(self, color_desc):
        q = "SELECT color_id FROM color_map WHERE color_desc = ?"
        res = self.execute(q, (color_desc, )).fetchone()
        if res == None:
            self.execute("INSERT INTO color_map(color_id, color_desc) VALUES (NULL, ?)", (color_desc,))
            res = self.execute(q, (color_desc, )).fetchone()
        return res
    def find_color_desc(self, color_id):
        q = "SELECT color_desc FROM color_map WHERE color_id = ?"
        return self.execute(q, (color_id,)).fetchone()
                                
