"""
UTXO Fetcher:

fetches information about unspent transaction outputs from
external source (according to config) and feeds it to 
CoinManager.
"""

from ngcccbase.services.blockchain import BlockchainInfoInterface, AbeInterface
from ngcccbase.services.electrum import ElectrumInterface
from ngcccbase.services.helloblock import HelloBlockInterface
from ngcccbase.services.chroma import ChromanodeInterface

import time
import Queue
import threading
import logging

DEFAULT_ELECTRUM_SERVER = "btc.it-zone.org"
DEFAULT_ELECTRUM_PORT = 50001

class BaseUTXOFetcher(object):
    def __init__(self, interface):
        self.interface = interface

    @classmethod
    def make_interface(cls, model, params):
        use = params.get('interface', 'chromanode')
        if model.testnet:
            if use not in ['chromanode', 'helloblock', 'abe_testnet']:
                use = 'chromanode'
        if use == 'chromanode':
            return ChromanodeInterface(None, model.testnet)
        elif use == 'helloblock':
            return HelloBlockInterface(model.testnet)
        elif use == 'blockchain.info':
            return BlockchainInfoInterface()
        elif use == 'abe_testnet':
            return AbeInterface()
        elif use == 'electrum':
            electrum_server = params.get(
                'electrum_server', DEFAULT_ELECTRUM_SERVER)
            electrum_port = params.get(
                'electrum_port', DEFAULT_ELECTRUM_PORT)
            return ElectrumInterface(electrum_server, electrum_port)
        else:
            raise Exception('Unknown service for UTXOFetcher!')        

    def scan_address(self, address):
        for data in self.interface.get_utxo(address):
            self.add_utxo(address, data)

class SimpleUTXOFetcher(BaseUTXOFetcher):
    def __init__(self, model, params):
        """Create a fetcher object given configuration in <params>
        """
        super(SimpleUTXOFetcher, self).__init__(
            self.make_interface(model, params))
        self.model = model

    def add_utxo(self, address, data):
        txhash = data[0]
        self.model.get_tx_db().add_tx_by_hash(txhash)

    def scan_all_addresses(self):
        wam = self.model.get_address_manager()
        for address_rec in wam.get_all_addresses():
            self.scan_address(address_rec.get_address())

class AsyncUTXOFetcher(BaseUTXOFetcher):

    def __init__(self, model, params):
        interface = self.make_interface(model, params)
        super(AsyncUTXOFetcher, self).__init__(interface)
        self.sleep_time = 1
        self.model = model
        self.hash_queue = Queue.Queue()
        self.address_list = []
        self.running = False
        self.lock = threading.Lock()

    def update(self):
        wam = self.model.get_address_manager()
        with self.lock:
            self.address_list = [ar.get_address()
                                 for ar in wam.get_all_addresses()]

        any_got_updates = False
        while not self.hash_queue.empty():
            got_updates = self.model.get_tx_db().add_tx_by_hash(self.hash_queue.get())
            any_got_updates = any_got_updates or got_updates
        return any_got_updates
            
    def add_utxo(self, address, data):
        txhash = data[0]
        self.hash_queue.put(txhash)

    def start_thread(self):
        thread = threading.Thread(target=self.thread_loop)
        thread.start()

    def stop(self):
        with self.lock:
            self.running = False

    def is_running(self):
        with self.lock:
            return self.running
        
    def thread_loop(self):
        with self.lock:
            self.running = True
        while self.is_running():
            try:
                with self.lock:
                    address_list = self.address_list[:]
                for address in address_list:
                    self.scan_address(address)
            except Exception as e:
                print e
            time.sleep(self.sleep_time)



