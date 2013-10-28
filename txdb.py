from coloredcoinlib.store import DataStore, DataStoreConnection

TX_STATUS_UNKNOWN = 0

class TxDataStore(DataStore):
    def __init__(self, conn):
        super(TxDataStore, self).__init__(conn)
        if not self.table_exists('tx_data'):
            self.execute("CREATE TABLE tx_data (id INTEGER PRIMARY KEY AUTOINCREMENT, \
txhash TEXT, data TEXT, status INTEGER)")
            self.execute("CREATE UNIQUE INDEX tx_data_txhash ON tx_data (txhash)")
        #if not self.table_exists('tx_addr_index'):
        #    self.execute("CREATE TABLE tx_addr_index (tx_id INTEGER, address TEXT)")
        #    self.execute("CREATE INDEX tx_addr_index_tx_id ON tx_addr_index (tx_id)")
        #    self.execute("CREATE INDEX tx_addr_index_address ON tx_addr_index (address)")
            
    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        self.execute("INSERT INTO tx_data (txhash, data, status) VALUES (?, ?, ?)",
                     (txhash, txdata, status))

    def get_tx_by_hash(self, txhash):
        return self.execute("SELECT * FROM tx_data WHERE txhash = ?",
                            (txhash, )).fetchone()

class TxDb(object):
    def __init__(self, model, config):
        self.model = model
        self.store = TxDataStore(self.model.utxo_man.store.conn)

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        self.store.add_tx(txhash, txdata, status)
