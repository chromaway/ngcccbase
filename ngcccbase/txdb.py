from coloredcoinlib.store import DataStore, DataStoreConnection, PersistentDictStore, unwrap1
from txcons import RawTxSpec
from time import time
from ngcccbase.services.blockchain import BlockchainInfoInterface

TX_STATUS_UNKNOWN = 0
TX_STATUS_UNCONFIRMED = 1
TX_STATUS_CONFIRMED = 2
TX_STATUS_INVALID = 3

create_transaction_table = """\
CREATE TABLE tx_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txhash TEXT,
    data TEXT,
    status INTEGER
);
"""

class TxDataStore(DataStore):
    def __init__(self, conn):
        super(TxDataStore, self).__init__(conn)
        if not self.table_exists('tx_data'):
            self.execute(create_transaction_table)
            self.execute(
                "CREATE UNIQUE INDEX tx_data_txhash ON tx_data (txhash)")

    def purge_tx_data(self):
        self.execute("DELETE FROM tx_data")

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        return self.execute(
            "INSERT INTO tx_data (txhash, data, status) VALUES (?, ?, ?)",
            (txhash, txdata, status))

    def set_tx_status(self, txhash, status):
        self.execute("UPDATE tx_data SET status = ? WHERE txhash = ?",
                     (status, txhash))
    
    def get_tx_status(self, txhash):
        return unwrap1(self.execute("SELECT status FROM tx_data WHERE txhash = ?",
                                    (txhash, )).fetchone())

    def get_tx_by_hash(self, txhash):
        return self.execute("SELECT * FROM tx_data WHERE txhash = ?",
                            (txhash, )).fetchone()


class BaseTxDb(object):
    def __init__(self, model, config):
        self.model = model
        self.store = TxDataStore(self.model.store_conn.conn)
        self.last_status_check = dict()
        self.recheck_interval = 60

    def purge_tx_db(self):
        self.store.purge_tx_data()

    def add_raw_tx(self, raw_tx, status=TX_STATUS_UNCONFIRMED):
        self.add_tx(raw_tx.get_hex_txhash(),
                    raw_tx.get_hex_tx_data(),
                    raw_tx,
                    status)

    def add_tx_by_hash(self, txhash, status=None):
        bs = self.model.get_blockchain_state()
        txdata = bs.get_raw(txhash)
        raw_tx = RawTxSpec.from_tx_data(self.model,
                                        txdata.decode('hex'))
        self.add_tx(txhash, txdata, raw_tx, status)

    def add_tx(self, txhash, txdata, raw_tx, status=None):
        if not self.store.get_tx_by_hash(txhash):
            if not status:
                status = self.identify_tx_status(txhash)
            self.store.add_tx(txhash, txdata, status)
            self.last_status_check[txhash] = time()
            self.model.get_coin_manager().apply_tx(txhash, raw_tx)
        else:
            self.maybe_recheck_tx_status(txhash, 
                                         self.store.get_tx_status(txhash))

    def recheck_tx_status(self, txhash):
        status = self.identify_tx_status(txhash)
        self.store.set_tx_status(txhash, status)
        return status
   
    def maybe_recheck_tx_status(self, txhash, status):
        if (time() - self.last_status_check.get(txhash, 0)) < self.recheck_interval:
            return status
        status = self.recheck_tx_status(txhash)
        self.last_status_check[txhash] = time()
        return status

    def is_tx_valid(self, txhash):
        status = self.store.get_tx_status(txhash)
        if status == TX_STATUS_CONFIRMED:
            return True
        status = self.maybe_recheck_tx_status(txhash, status)
        return status != TX_STATUS_INVALID

    def is_tx_confirmed(self, txhash):
        status = self.store.get_tx_status(txhash)
        if status != TX_STATUS_CONFIRMED:
            status = self.maybe_recheck_tx_status(txhash, status)
        return status == TX_STATUS_CONFIRMED


class NaiveTxDb(BaseTxDb):
    """Native TxDb trusts results of get_blockchain_state"""
    def identify_tx_status(self, txhash):
        block_hash, in_mempool = self.model.get_blockchain_state().\
            get_tx_blockhash(txhash)
        if block_hash:
            return TX_STATUS_CONFIRMED
        elif in_mempool:
            return TX_STATUS_UNCONFIRMED
        else:
            return TX_STATUS_INVALID

class BCI_TxDb(BaseTxDb):
    """TxDb which trusts data it gets from Blockchain.info"""
    
    def __init__(self, model, config):
        super(BCI_TxDb, self).__init__(model, config)
        self.confirmed_txs = set()

    def notify_confirmations(self, txhash, confirmations):
        if confirmations >= 1:
            self.confirmed_txs.add(txhash)

    def identify_tx_status(self, txhash):
        if txhash in self.confirmed_txs:
            return TX_STATUS_CONFIRMED
        bci_interface = self.model.utxo_fetcher.interface
        assert isinstance(bci_interface, BlockchainInfoInterface)
        confirmations = bci_interface.get_tx_confirmations(txhash)
        if confirmations > 0:
            self.confirmed_txs.add(txhash)
            return TX_STATUS_CONFIRMED
        elif confirmations == 0:
            return TX_STATUS_UNCONFIRMED
        else:
            return TX_STATUS_INVALID
