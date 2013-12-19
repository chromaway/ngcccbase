from coloredcoinlib.store import DataStore, DataStoreConnection

import utxodb

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
        #if not self.table_exists('tx_addr_index'):
        #    self.execute(
        #        "CREATE TABLE tx_addr_index (tx_id INTEGER, address TEXT)")
        #    self.execute(
        #        "CREATE INDEX tx_addr_index_tx_id ON tx_addr_index (tx_id)")
        #    self.execute(
        #      "CREATE INDEX tx_addr_index_address ON tx_addr_index (address)")

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        return self.execute(
            "INSERT INTO tx_data (txhash, data, status) VALUES (?, ?, ?)",
            (txhash, txdata, status))

    def add_signed_tx(self, txhash, tx):
        insert_transaction = """\
        INSERT INTO tx_address (
            address,
            type,
            txid
        ) VALUES(?, ?, ?)"""
        with self.transaction():
            txid = self.add_tx(txhash, tx.get_hex_tx_data()).lastrowid

            for txin in tx.composed_tx_spec.txins:
                if isinstance(txin, utxodb.UTXO) and txin.address_rec:
                    self.execute(
                        insert_transaction,
                        (txin.address_rec.address, TXIN, txid))

            for txout in tx.composed_tx_spec.txouts:
                if isinstance(txout.target_addr, str):
                    self.execute(
                        insert_transaction, (txout.target_addr, TXOUT, txid))

    def get_tx_by_hash(self, txhash):
        return self.execute("SELECT * FROM tx_data WHERE txhash = ?",
                            (txhash, )).fetchone()

    def get_tx_by_output_address(self, address):
        select_tx = """\
        SELECT txhash, data, status
         FROM tx_data
        JOIN tx_address ON tx_data.id = tx_address.txid
        WHERE tx_address.address = ?
        """
        return self.execute(select_tx, (address,))


class TxDb(object):
    def __init__(self, model, config):
        self.model = model
        self.store = TxDataStore(self.model.store_conn.conn)

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        self.store.add_tx(txhash, txdata, status)

    def add_signed_tx(self, txhash, tx):
        self.store.add_signed_tx(txhash, tx)
