from coloredcoinlib.store import DataStore
from time import time

class UTXOStore(DataStore):
    def __init__(self, conn):
        super(UTXOStore, self).__init__(conn)
        if not self.table_exists('utxo_data'):
            self.execute("CREATE TABLE utxo_data (id  INTEGER PRIMARY KEY AUTOINCREMENT, \
address TEXT,\
txhash TEXT, outindex INTEGER, value INTEGER, script TEXT,\
scantime INTEGER, commitment INTEGER)")
            self.execute("CREATE UNIQUE INDEX utxo_data_outpoint ON utxo_data (txhash, outindex)")
            self.execute("CREATE INDEX utxo_data_address ON utxo_data (address)")
            self.execute("CREATE INDEX utxo_data_scantime ON utxo_data (scantime)")
            self.execute("CREATE INDEX utxo_data_commitment ON utxo_data (commitment)")

    
    def add_utxo(self, address, address, txhash, outindex, value, script, scantime=None, commitment=0):
        if not scantime:
            scantime = int(time()) 
        self.execute("INSERT INTO utxo_data (address, txhash, outindex, value, script, scantime, commitment)\
VALUES (?, ?, ?, ?, ?, ?)", 
                     (address, txhash, outindex, value, script, scantime, commitment))

    def del_utxo(self, txhash, outindex):
        self.execute("DELETE FROM utxo_data WHERE txhash = ? AND outindex = ?",
                     (txhash, outindex))
    
    def delete_all(self):
        self.execute("DELETE FROM utxo_data")

    def get_all_utxos(self):
        return self.execute("SELECT * FROM utxo_data").fetchall()

    def get_utxos_by_address(self, address):
        return self.execute("SELECT * FROM utxo_data WHERE address = ?", (address, )).fetchall()
                         
class UTXOManager(object):
    def __init__(self, model, store, txdata):
        self.model = model
        self.store = store
        self.txdata
        
    def update_address(self, address):
        utxo_list = self.txdata.unspent.get_for_address(address)
        for utxo in utxo_list:
            self.store.add_utxo(address, utxo.txhash, utxo.outindex,
                                utxo.value, utxo.script)

    def update_all(self):
        self.store.delete_all()
        wam = self.model.get_address_manager()
        for address in wam.get_all_addresses():
            self.update_address(address)
