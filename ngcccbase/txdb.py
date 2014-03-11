from coloredcoinlib.store import DataStore, DataStoreConnection, PersistentDictStore

TX_STATUS_UNKNOWN = 0

create_transaction_table = """\
CREATE TABLE tx_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txhash TEXT,
    data TEXT,
    status INTEGER
);
"""

create_address_table = """\
CREATE TABLE tx_address (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT,
    type INTEGER,
    txid INTEGER,
    coloring TEXT,
    FOREIGN KEY(txid) REFERENCES tx_data(id)
);
"""

TXIN = 0
TXOUT = 1


class TxDataStore(DataStore):
    def __init__(self, conn):
        super(TxDataStore, self).__init__(conn)
        if not self.table_exists('tx_data'):
            self.execute(create_transaction_table)
            self.execute(
                "CREATE UNIQUE INDEX tx_data_txhash ON tx_data (txhash)")
        if not self.table_exists('tx_address'):
            self.execute(create_address_table)             

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        return self.execute(
            "INSERT INTO tx_data (txhash, data, status) VALUES (?, ?, ?)",
            (txhash, txdata, status))

    def add_signed_tx(self, txhash, tx):
        """we no longer need to populate tx_address, 
        we use coindb instead"""
        return self.add_tx(txhash, tx.get_hex_tx_data())

    def get_tx_by_hash(self, txhash):
        return self.execute("SELECT * FROM tx_data WHERE txhash = ?",
                            (txhash, )).fetchone()

    def get_tx_by_output_address(self, address):
        return []


class TxDb(object):
    def __init__(self, model, config):
        self.model = model
        self.store = TxDataStore(self.model.store_conn.conn)
        self.intents = PersistentDictStore(self.model.store_conn.conn,
                                           "tx_intents")

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        self.store.add_tx(txhash, txdata, status)

    def add_signed_tx(self, txhash, tx):
        self.store.add_signed_tx(txhash, tx)

    def add_tx_intent(self, txhash, intent):
        self.intents[txhash] = intent

    def get_tx_intent(self, txhash):
        if txhash in self.intents:
            return self.intents[txhash]
        else:
            return None
