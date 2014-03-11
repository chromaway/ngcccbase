"""
coindb.py

Keeps track of transaction outputs (coins) which belong to user's wallet.
CoinQuery is able to find transaction outputs satisfying certain criteria:

 * belonging to a particular color set (incl. uncolored)
 * confirmed/unconfirmed
 * spent/unspent

Information about coins is added either by UTXO fetcher or by wallet
controller through apply_tx.
"""

from coloredcoinlib.store import DataStore, DataStoreConnection, unwrap1
from coloredcoinlib.txspec import ComposedTxSpec
from txcons import RawTxSpec
from coloredcoinlib import UNCOLORED_MARKER, SimpleColorValue

def flatten1(lst):
    return [elt[0] for elt in lst]
        

class CoinStore(DataStore):
    """Storage for Coin (Transaction Objects).
    """
    def __init__(self, conn):
        """Create a unspent transaction out data-store at <dbpath>.
        """
        super(CoinStore, self).__init__(conn)
        if not self.table_exists('coin_data'):
            # create the main table and some useful indexes
            self.execute("""
                CREATE TABLE coin_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT,
                    txhash TEXT, outindex INTEGER, value INTEGER,
                    script TEXT)
            """)
            self.execute("CREATE UNIQUE INDEX coin_data_outpoint ON coin_data "
                         "(txhash, outindex)")
            self.execute("CREATE INDEX coin_data_address ON coin_data "
                         "(address)")
        if not self.table_exists('coin_spends'):
            self.execute("""
                 CREATE TABLE coin_spends (coin_id INTEGER, txhash TEXT,
                               FOREIGN KEY (coin_id) REFERENCES coin_data(id))""")
            self.execute("CREATE UNIQUE INDEX coin_spends_id ON coin_spends "
                         "(coin_id, txhash)")
            self.execute("CREATE INDEX coin_spends_txhash ON coin_spends "
                         "(txhash)")
        if not self.table_exists("coin_blocks"):
            self.execute("""CREATE TABLE coin_blocks
                    (coin_id INTEGER, block_hash TEXT,
                     FOREIGN KEY (coin_id) REFERENCES coin_data(id))""")
            self.execute("CREATE UNIQUE INDEX coin_blocks_id ON coin_blocks "
                         "(coin_id, block_hash)")
        if not self.table_exists("tx_confirmations"):
            self.execute("""CREATE TABLE tx_confirmations (txhash TEXT PRIMARY KEY,
                            confirmations INTEGER)""")

    def purge_coins(self):
        self.execute("DELETE FROM coin_blocks")
        self.execute("DELETE FROM coin_spends")
        self.execute("DELETE FROM tx_confirmations")
        self.execute("DELETE FROM coin_data")

    def add_coin(self, address, txhash, outindex, value, script):
        """Record a coin into the sqlite3 DB. We record the following
        values:
        <address>    - bitcoin address of the coin
        <txhash>     - b58 encoded transaction hash
        <outindex>   - position of the coin within the greater transaction
        <value>      - amount in Satoshi being sent
        <script>     - signature
        """
        self.execute(
            """INSERT INTO coin_data
               (address, txhash, outindex, value, script)
               VALUES (?, ?, ?, ?, ?)""",
            (address, txhash, outindex, value, script))
    
    def add_spend(self, coin_id, spend_txhash):
        self.execute("INSERT OR IGNORE INTO coin_spends (coin_id, txhash) VALUES (?, ?)",
                     (coin_id, spend_txhash))

    def add_coin_block(self, coin_id, block_hash):
        self.execute("INSERT OR IGNORE INTO coin_blocks (coin_id, block_hash) VALUES (?, ?)",
                     (coin_id, block_hash))
    
    def find_coin(self, txhash, outindex):
         return unwrap1(self.execute("SELECT id FROM coin_data WHERE txhash = ? and outindex = ?",
                                     (txhash, outindex)).fetchone())

    def get_coin_spends(self, coin_id):
        return flatten1(self.execute("SELECT txhash FROM coin_spends WHERE coin_id = ?",
                                     (coin_id, )).fetchall())

    def get_unconfirmed(self):
        return flatten1(self.execute("SELECT coin_data.id FROM coin_data LEFT JOIN\
 coin_blocks ON coin_data.id = coin_blocks.coin_id WHERE coin_id IS NULL").fetchall())

    def get_tx_confirmations(self, txhash):
        res = self.execute("SELECT confirmations FROM tx_confirmations WHERE txhash = ?",
                           (txhash, )).fetchone()
        if res:
            return res[0]
        else:
            return 0

    def set_tx_confirmations(self, txhash, confirmations):
        self.execute("""INSERT OR REPLACE INTO tx_confirmations (txhash, confirmations)
                        VALUES (?, ?)""", (txhash, confirmations))
    
    def get_coin_blocks(self, coin_id):
        return flatten1(self.execute("SELECT block_hash FROM coin_blocks WHERE coin_id = ?",
                                     (coin_id, )).fetchall())

    def get_coins_for_address(self, address):
        """Return the entire list of coins for a given address <address>
        """
        return self.execute("SELECT * FROM coin_data WHERE address = ?",
                            (address, )).fetchall()

    def get_coin(self, coin_id):
        return self.execute("SELECT * FROM coin_data WHERE id = ?",
                            (coin_id,)).fetchone()

class Coin(ComposedTxSpec.TxIn):
    def __init__(self, coin_manager, coin_data):
        super(Coin, self).__init__(coin_data['txhash'], coin_data['outindex'])
        self.txhash = coin_data['txhash']
        self.outindex = coin_data['outindex']
        self.value = coin_data['value']
        self.script = coin_data['script']
        self.address_rec = None
        self.colorvalues = None
        self.coin_id = coin_data['id']
        self.coin_manager = coin_manager

    def is_spent(self):
        return self.coin_manager.is_spent(self)
    
    def is_confirmed(self):
        return self.coin_manager.is_confirmed(self)
        
class CoinQuery(object):
    """Query object for getting data out of the UTXO data-store.
    """
    def __init__(self, model, color_set, filter_options):
        """Create a query object given a wallet_model <model> and
        a list of colors in <color_set>
        """
        self.model = model
        self.color_set = color_set
        self.coin_manager = model.get_coin_manager()
        self.filter_options = filter_options
        assert 'spent' in filter_options

    def coin_matches_filter(self, coin):
        if self.filter_options['spent'] != coin.is_spent():
            return False
        if self.filter_options.get('only_unconfirmed', False):
            return not coin.is_confirmed()
        if self.filter_options.get('include_unconfirmed', False):
            return True
        return coin.is_confirmed()    

    def get_coins_for_address(self, address_rec):
        """Given an address <address_rec>, return the list of coin's
        straight from the DB. Note this specifically does NOT return
        COIN objects.
        """
        color_set = self.color_set
        addr_color_set = address_rec.get_color_set()
        all_coins = filter(
            self.coin_matches_filter,
            self.coin_manager.get_coins_for_address(address_rec.get_address()))
        cdata = self.model.ccc.colordata
        address_is_uncolored = addr_color_set.color_id_set == set([0])
        if address_is_uncolored:
            for coin in all_coins:
                coin.address_rec = address_rec
                coin.colorvalues = [SimpleColorValue(colordef=UNCOLORED_MARKER,
                                                     value=coin.value)]
            return all_coins
        for coin in all_coins:
            coin.address_rec = address_rec
            coin.colorvalues = None
            try:
                coin.colorvalues = cdata.get_colorvalues(
                    addr_color_set.color_id_set, coin.txhash, coin.outindex)
            except Exception as e:
                print e
                raise
        def relevant(coin):
            cvl = coin.colorvalues
            if coin.colorvalues is None:
                return False  # None indicates failure
            if cvl == []:
                return color_set.has_color_id(0)
            for cv in cvl:
                if color_set.has_color_id(cv.get_color_id()):
                    return True
                return False
        return filter(relevant, all_coins)

    def get_result(self):
        """Returns all utxos for the color_set defined for this query.
        """
        addr_man = self.model.get_address_manager()
        addresses = addr_man.get_addresses_for_color_set(self.color_set)
        utxos = []
        for address in addresses:
            utxos.extend(self.get_coins_for_address(address))
        return utxos


class CoinManager(object):
    """Object for managing the UTXO data store.
    Note using this manager allows us to create multiple UTXO data-stores.
    """
    def __init__(self, model, config):
        """Creates a UTXO manager given a wallet_model <model>
        and configuration <config>.
        """
        params = config.get('utxodb', {})
        self.model = model
        self.full_spv = params.get('full_spv', model.testnet)
        self.store = CoinStore(self.model.store_conn.conn)
        self.tx_confirmations = dict()

    def purge_coins(self):
        """full rescan"""
        self.store.purge_coins()

    def get_coin(self, coin_id):
        coin_rec = self.store.get_coin(coin_id)
        if coin_rec:
            return Coin(self.store, coin_rec)
        else:
            return None

    def is_spent(self, coin):
        return len(self.store.get_coin_spends(coin.coin_id)) > 0

    def is_confirmed(self, coin):
        if self.full_spv:
            blocks = self.store.get_coin_blocks(coin.coin_id)
            return len(blocks) > 0
        else:
            return self.store.get_tx_confirmations(coin.txhash) > 0

    def notify_confirmations(self, txhash, confirmations):
        self.store.set_tx_confirmations(txhash, confirmations)

    def get_coins_for_address(self, address):
        """Returns a list of UTXO objects for a given address <address>
        """
        coins = []
        for coin_rec in self.store.get_coins_for_address(address):
            coin = Coin(self, coin_rec)
            coins.append(coin)
        return coins

    def add_coin(self, address, txhash, outindex, value, script, block_hash=None):
        coin_id = self.store.find_coin(txhash, outindex)
        if coin_id is None:
            self.store.add_coin(address, txhash, outindex, value, script)
            coin_id = self.store.find_coin(txhash, outindex)
        if block_hash:
            self.update_coin_block_hash(coin_id, block_hash)

    def update_confirmations(self):
        if not self.full_spv:
            return
        for coin_id in self.store.get_unconfirmed():
            coin = self.get_coin(coin_id)
            block_hash = self.model.ccc.blockchain_state.get_tx_blockhash(coin.txhash)
            if block_hash:
                self.update_coin_block_hash(coin_id, block_hash)
        
    def update_coin_block_hash(self, coin_id, block_hash):
        if not self.full_spv:
            return
        if coin_id and (block_hash not in self.store.get_coin_blocks(coin_id)):
            self.store.add_coin_block(coin_id, block_hash)

    def apply_tx(self, txhash, tx=None):
        """Given a transaction <composed_tx_spec>, delete any
        utxos that it spends and add any utxos that are new
        """

        all_addresses = [a.get_address() for a in
                         self.model.get_address_manager().get_all_addresses()]

        bs = self.model.ccc.blockchain_state
        if self.full_spv:
            block_hash, _ = bs.get_tx_blockhash(txhash)
        else:
            block_hash = None
        if not tx:
            raw_tx = bs.get_raw(txhash).decode('hex')
            tx = RawTxSpec.from_tx_data(self.model, raw_tx)

        # record spends
        for txin in tx.composed_tx_spec.txins:
            prev_txhash, prev_outindex = txin.get_outpoint()
            coin_id = self.store.find_coin(prev_txhash, prev_outindex)
            if coin_id:
                self.store.add_spend(coin_id, txhash)
                
        # put the new utxo into the db
        for i, txout in enumerate(tx.composed_tx_spec.txouts):
            script = tx.pycoin_tx.txs_out[i].script.encode('hex')
            if txout.target_addr in all_addresses:
                self.add_coin(txout.target_addr, txhash, i,
                              txout.value, script, block_hash)
                             
