#!/usr/bin/env python

"""
utxodb.py

Unspent Transaction Out library.
Because of how colored coins work, it is essential that we keep
a very detailed record of exactly what unspent transactions exist.
Specifically, obc (order-based-coloring) approach requires that we
keep track of exactly which coins went where as the order in which
the addresses are recorded into the bitcoin blockchain determines
exactly where the colored coin goes.

Note that a transaction consists of a bunch of tx-in's and tx-outs.
We only care about the Unspent TX-Outs. The sum of these is the
bitcoin balance. The components will tell us how much of a balance
of each colored coin we have.
"""

from coloredcoinlib.store import DataStore, DataStoreConnection
from coloredcoinlib.txspec import ComposedTxSpec
from coloredcoinlib import UNCOLORED_MARKER, SimpleColorValue
from txcons import RawTxSpec
from time import time
from ngcccbase.services.blockchain import BlockchainInfoInterface, AbeInterface
from ngcccbase.services.electrum import ElectrumInterface



import sqlite3
import urllib2
import json

DEFAULT_ELECTRUM_SERVER = "btc.it-zone.org"
DEFAULT_ELECTRUM_PORT = 50001


class UTXOStore(DataStore):
    """Storage for Unspent Transaction Objects.
    This is done by recording utxo's in a sqlite3 database.
    """
    def __init__(self, conn):
        """Create a unspent transaction out data-store at <dbpath>.
        """
        super(UTXOStore, self).__init__(conn)
        if not self.table_exists('utxo_data'):
            # create the main table and some useful indexes
            self.execute("""
                CREATE TABLE utxo_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT,
                    txhash TEXT, outindex INTEGER, value INTEGER,
                    script TEXT, scantime INTEGER, commitment INTEGER)
            """)
            self.execute("CREATE UNIQUE INDEX utxo_data_outpoint ON utxo_data "
                         "(txhash, outindex)")
            self.execute("CREATE INDEX utxo_data_address ON utxo_data "
                         "(address)")
            self.execute("CREATE INDEX utxo_data_scantime ON utxo_data "
                         "(scantime)")
            self.execute("CREATE INDEX utxo_data_commitment ON utxo_data "
                         "(commitment)")

    def add_utxo(self, address, txhash, outindex, value, script,
                 scantime=None, commitment=0):
        """Record a utxo into the sqlite3 DB. We record the following
        values:
        <address>    - bitcoin address of the utxo
        <txhash>     - b58 encoded transaction hash
        <outindex>   - position of the utxo within the greater transaction
        <value>      - amount in Satoshi being sent
        <script>     - signature
        <scantime>   - time we got this transaction (optional)
        <commitment> - number of confirms this transaction has (optional)
        """
        if not scantime:
            scantime = int(time())
        self.execute(
            """INSERT INTO utxo_data
               (address, txhash, outindex, value, script, scantime, commitment)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (address, txhash, outindex, value, script, scantime, commitment))

    def del_utxo(self, txhash, outindex):
        """Remove a utxo from the sqlite3 DB with transaction <txhash>
        at the <outindex> position.
        """
        self.execute(
            "DELETE FROM utxo_data WHERE txhash = ? AND outindex = ?",
            (txhash, outindex))

    def delete_all(self):
        """Remove all utxos from the database.
        """
        self.execute("DELETE FROM utxo_data")

    def get_all_utxos(self):
        """Return the entire list of all utxos from the database.
        Please use with caution.
        """
        return self.execute("SELECT * FROM utxo_data").fetchall()

    def get_utxos_for_address(self, address):
        """Return the entire list of utxos for a given address <address>
        """
        return self.execute("SELECT * FROM utxo_data WHERE address = ?",
                            (address, )).fetchall()


class UTXOQuery(object):
    """Query object for getting data out of the UTXO data-store.
    """
    def __init__(self, model, color_set):
        """Create a query object given a wallet_model <model> and
        a list of colors in <color_set>
        """
        self.model = model
        self.color_set = color_set
        self.utxo_manager = model.get_utxo_manager()

    def get_utxos_for_address(self, address_rec):
        """Given an address <address_rec>, return the list of utxo's
        straight from the DB. Note this specifically does NOT return
        UTXO objects.
        """
        color_set = self.color_set
        addr_color_set = address_rec.get_color_set()
        all_utxos = self.utxo_manager.get_utxos_for_address(
            address_rec.get_address())
        cdata = self.model.ccc.colordata
        address_is_uncolored = addr_color_set.color_id_set == set([0])
        if address_is_uncolored:
            for utxo in all_utxos:
                utxo.address_rec = address_rec
                utxo.colorvalues = [SimpleColorValue(colordef=UNCOLORED_MARKER,
                                                     value=utxo.value)]
            return all_utxos
        for utxo in all_utxos:
            utxo.address_rec = address_rec
            utxo.colorvalues = None
            try:
                utxo.colorvalues = cdata.get_colorvalues(
                    addr_color_set.color_id_set, utxo.txhash, utxo.outindex)
            except Exception as e:
                print e
        def relevant(utxo):
            cvl = utxo.colorvalues
            if utxo.colorvalues is None:
                return False  # None indicates failure
            if cvl == []:
                return color_set.has_color_id(0)
            for cv in cvl:
                if color_set.has_color_id(cv.get_color_id()):
                    return True
                return False
        return filter(relevant, all_utxos)

    def get_result(self):
        """Returns all utxos for the color_set defined for this query.
        """
        addr_man = self.model.get_address_manager()
        addresses = addr_man.get_addresses_for_color_set(self.color_set)
        utxos = []
        for address in addresses:
            utxos.extend(self.get_utxos_for_address(address))
        return utxos


class UTXO(ComposedTxSpec.TxIn):
    """Unspent Transaction Output object
    Unspent Transaction Outputs are parts of a Transaction that haven't
    been spent yet. Since ordering is important for obc (order-based coloring),
    we use these objects to figure out how much of each colored coin we
    have.
    """
    def __init__(self, txhash, outindex, value, script):
        """Create a UTXO object for a given transaction with hash <txhash>
        at the position <outindex> that consists of <value> Satoshis
        with a signature <script>
        """
        super(UTXO, self).__init__(txhash, outindex)
        self.txhash = txhash  # TODO: duplicated, remove
        self.outindex = outindex
        self.value = value
        self.script = script
        self.address_rec = None
        self.colorvalues = None
        self.utxo_rec = None

    def __repr__(self):
        return "%s %s %s %s" % (
            self.txhash, self.outindex, self.value, self.script)


class UTXOFetcher(object):
    """Object which can fetch UTXO's. The main sources are:
    blockchain - blockchain.info can provide utxos through JSON
    testnet    - an open-source block explorer using JSON
    electrum   - stratum-protocol servers
    """
    def __init__(self, params):
        """Create a fetcher object given configuration in <params>
        """
        use = params.get('interface', 'blockchain.info')
        if use == 'blockchain.info':
            self.interface = BlockchainInfoInterface()
        elif use == 'testnet':
            self.interface = AbeInterface()
        elif use == 'electrum':
            electrum_server = params.get(
                'electrum_server', DEFAULT_ELECTRUM_SERVER)
            electrum_port = params.get(
                'electrum_port', DEFAULT_ELECTRUM_PORT)
            self.interface = ElectrumInterface(electrum_server, electrum_port)
        else:
            raise Exception('unknown service for UTXOFetcher')

    def get_for_address(self, address):
        """Returns a UTXO object list for a given address <address>.
        """
        objs = []
        for data in self.interface.get_utxo(address):
            objs.append(UTXO(*data))
        return objs


class UTXOManager(object):
    """Object for managing the UTXO data store.
    Note using this manager allows us to create multiple UTXO data-stores.
    """
    def __init__(self, model, config):
        """Creates a UTXO manager given a wallet_model <model>
        and configuration <config>.
        """
        params = config.get('utxodb', {})
        if config.get('testnet', False):
            fetcher_config = dict(interface="testnet")
        else:
            fetcher_config = params.get('utxo_fetcher', {})
        self.model = model
        self.store = UTXOStore(self.model.store_conn.conn)
        self.utxo_fetcher = UTXOFetcher(fetcher_config)

    def get_utxos_for_address(self, address):
        """Returns a list of UTXO objects for a given address <address>
        """
        utxos = []
        for utxo_rec in self.store.get_utxos_for_address(address):
            utxo = UTXO(utxo_rec['txhash'], utxo_rec['outindex'],
                        utxo_rec['value'], utxo_rec['script'])
            utxo.utxo_rec = utxo_rec
            utxos.append(utxo)
        return utxos

    def update_address(self, address_rec):
        """Given an address <address_rec>, update the utxo records.
        """
        try:
            address = address_rec.get_address()
            utxo_list = self.utxo_fetcher.get_for_address(address)
            for utxo in utxo_list:
                self.store.add_utxo(address, utxo.txhash, utxo.outindex,
                                    utxo.value, utxo.script)
        except Exception as e:
            if "%s" % e != "No JSON object could be decoded":
                print e

    def update_all(self):
        """Update all utxos for addresses associated with the wallet.
        """
        self.store.delete_all()
        wam = self.model.get_address_manager()
        alladdresses = wam.get_all_addresses()
        for address in alladdresses:
            self.update_address(address)
        mempool = self.model.ccc.blockchain_state.get_mempool_txs()
        dels = []
        for tx in mempool:
            self.apply_tx(tx.hash)

    def apply_tx(self, txhash, tx=None):
        """Given a transaction <composed_tx_spec>, delete any
        utxos that it spends and add any utxos that are new
        """

        all_addresses = [a.get_address() for a in
                         self.model.get_address_manager().get_all_addresses()]

        if not tx:
            bs = self.model.ccc.blockchain_state
            raw_tx = bs.bitcoind.getrawtransaction(txhash, 0).decode('hex')
            tx = RawTxSpec.from_tx_data(self.model, raw_tx)

        # delete the spent utxo from the db
        for txin in tx.composed_tx_spec.txins:
            oldtxhash, outindex = txin.get_outpoint()
            self.store.del_utxo(oldtxhash, outindex)

        # put the new utxo into the db
        for i, txout in enumerate(tx.composed_tx_spec.txouts):
            script = tx.pycoin_tx.txs_out[i].script.encode('hex')
            if txout.target_addr in all_addresses:
                self.store.add_utxo(txout.target_addr, txhash, i,
                                    txout.value, script)


if __name__ == "__main__":
    # test the UTXOFetcher
    uf = UTXOFetcher(dict(interface='testnet'))
    print (uf.get_for_address("n3kJcsapnFU5Gna9Y1dMwDNpbTFVmYFR4o"))
