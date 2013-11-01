from coloredcoinlib.store import DataStore, DataStoreConnection
from time import time
from blockchain import BlockchainInterface
from electrum import ElectrumInterface
import sqlite3
import urllib2
import json

ELECTRUM_SERVER = "btc.it-zone.org"
ELECTRUM_PORT = 50001

class UTXOStore(DataStore):
    def __init__(self, dbpath):
        self.dsconn = DataStoreConnection(dbpath)
        super(UTXOStore, self).__init__(self.dsconn.conn)
        self.dsconn.conn.row_factory = sqlite3.Row
        if not self.table_exists('utxo_data'):
            self.execute("CREATE TABLE utxo_data (id  INTEGER PRIMARY KEY AUTOINCREMENT, \
address TEXT,\
txhash TEXT, outindex INTEGER, value INTEGER, script TEXT,\
scantime INTEGER, commitment INTEGER)")
            self.execute("CREATE UNIQUE INDEX utxo_data_outpoint ON utxo_data (txhash, outindex)")
            self.execute("CREATE INDEX utxo_data_address ON utxo_data (address)")
            self.execute("CREATE INDEX utxo_data_scantime ON utxo_data (scantime)")
            self.execute("CREATE INDEX utxo_data_commitment ON utxo_data (commitment)")
    
    def add_utxo(self, address, txhash, outindex, value, script, scantime=None, commitment=0):
        if not scantime:
            scantime = int(time()) 
        self.execute("INSERT INTO utxo_data (address, txhash, outindex, value, script, scantime, commitment)\
VALUES (?, ?, ?, ?, ?, ?, ?)", 
                     (address, txhash, outindex, value, script, scantime, commitment))

    def del_utxo(self, txhash, outindex):
        self.execute("DELETE FROM utxo_data WHERE txhash = ? AND outindex = ?",
                     (txhash, outindex))
    
    def delete_all(self):
        self.execute("DELETE FROM utxo_data")

    def get_all_utxos(self):
        return self.execute("SELECT * FROM utxo_data").fetchall()

    def get_utxos_for_address(self, address):
        return self.execute("SELECT * FROM utxo_data WHERE address = ?", (address, )).fetchall()

class UTXOQuery(object):
    """can be used to request UTXOs satisfying certain criteria"""
    def __init__(self, model, color_set):
        self.model = model
        self.color_set = color_set
        self.utxo_manager = model.get_utxo_manager()

    def get_utxos_for_address(self, address_rec):
        color_set = self.color_set    
        addr_color_set = address_rec.get_color_set()
        all_utxos = self.utxo_manager.get_utxos_for_address(address_rec.get_address())
        cdata = self.model.ccc.colordata        
        address_is_uncolored = addr_color_set.color_id_set == set([0])
        for utxo in all_utxos:
            utxo.address_rec = address_rec
            if not address_is_uncolored:
                utxo.colorvalues = cdata.get_colorstates(addr_color_set.color_id_set,
                                                         utxo.txhash, utxo.outindex)
        if address_is_uncolored:
            return all_utxos
        else:
            def relevant(utxo):
                cvl = utxo.colorvalues
                if not cvl:
                    return color_set.has_color_id(0)
                for cv in cvl:
                    if color_set.has_color_id(cv[0]):
                        return True
                    return False
            return filter(relevant, all_utxos)

    def get_result(self):
        addr_man = self.model.get_address_manager()
        addresses = addr_man.get_addresses_for_color_set(self.color_set)
        utxos = []
        for address in addresses:
            utxos.extend(self.get_utxos_for_address(address))
        return utxos

class UTXO(object):
    """represents an unspent transaction output"""
    def __init__(self, txhash, outindex, value, script):
        self.txhash = txhash
        self.outindex = outindex
        self.value = value
        self.script = script
        self.address_rec = None
        self.colorvalues = None
        self.utxo_rec = None

    def get_pycoin_coin_source(self):
        """returns utxo object data as pycoin utxo data for use with pycoin transaction construction"""
        import pycoin.tx
        le_txhash = self.txhash.decode('hex')[::-1]
        pycoin_txout = pycoin.tx.TxOut(self.value, self.script.decode('hex'))
        return (le_txhash, self.outindex, pycoin_txout)

    def __repr__(self):
        return "%s %s %s %s" % (self.txhash, self.outindex, self.value, self.script)

class UTXOFetcher(object):
    def __init__(self):
        self.electrum_interface = ElectrumInterface(ELECTRUM_SERVER, ELECTRUM_PORT)

    """ Fetches UTXO's for specific address"""
    def get_for_address(self, address):
        objs = []
        for data in self.electrum_interface.get_utxo(address):
            objs.append(UTXO(*data))
        return objs

class UTXOManager(object):
    def __init__(self, model, config):
        params = config.get('utxodb', {})
        self.model = model
        self.store = UTXOStore(params.get('dbpath', "utxo.db"))
        self.utxo_fetcher = UTXOFetcher()

    def get_utxos_for_address(self, address):
        utxos = []
        for utxo_rec in self.store.get_utxos_for_address(address):
            utxo = UTXO(utxo_rec['txhash'], utxo_rec['outindex'],
                        utxo_rec['value'], utxo_rec['script'])
            utxo.utxo_rec = utxo_rec
            utxos.append(utxo)
        return utxos
        
    def update_address(self, address_rec):
        try:
            address = address_rec.get_address()
            utxo_list = self.utxo_fetcher.get_for_address(address)
            for utxo in utxo_list:
                self.store.add_utxo(address, utxo.txhash, utxo.outindex,
                                    utxo.value, utxo.script)
        except Exception as e:
            print e

    def update_all(self):
        self.store.delete_all()
        wam = self.model.get_address_manager()
        for address in wam.get_all_addresses():
            self.update_address(address)

if __name__ == "__main__":
    uf = UTXOFetcher()
    print uf.get_for_address("1PAMLeDxXK3DJ4nm6okVHmjH7pmsbg8NYr")
