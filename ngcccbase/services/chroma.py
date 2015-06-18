#!/usr/bin/env python

import json
import urllib2
import time
import threading
from pycoin.tx.Tx import Tx
from ngcccbase.blockchain import BaseStore
from coloredcoinlib import BlockchainStateBase


class ChromanodeInterface(BlockchainStateBase, BaseStore):

    def __init__(self, baseurl=None, testnet=False):

        # Chromanode api documentation.
        # https://github.com/chromaway/chromanode/blob/master/docs/API_v1.md
        testnet_baseurl = "http://v1.testnet.bitcoin.chromanode.net"
        mainnet_baseurl = "http://v1.livenet.bitcoin.chromanode.net"
        default_baseurl = testnet_baseurl if testnet else mainnet_baseurl
        self.baseurl = baseurl if baseurl else default_baseurl

        # init caches
        self._cache_rawtx = {}  # txid -> rawtx
        self._cache_currentheight = 0
        self._last_connected = 0
        self._update_height_interval = 10
        self._thread = None
        self._update_height()
        self.connect()

    def _update_height(self):
        queryurl = "%s/v1/headers/latest" % self.baseurl
        self._cache_currentheight = self._query(queryurl)["height"]

    def connect(self):
        class _Thread(threading.Thread):

            def __init__(self, service):
                threading.Thread.__init__(self)
                self._stop = threading.Event()
                self.service = service

            def stop(self):
                self._stop.set()

            def run(self):
                while not self._stop.is_set():
                    self.service._update_height()
                    time.sleep(self.service._update_height_interval)

        self._thread = _Thread(self)
        self._thread.start()

    def connected(self):
        delta = time.time() - self._last_connected
        return delta < (self._update_height_interval + 1)

    def disconnect(self):
        self._thread.stop()
        self._thread = None

    def _query(self, url, data=None, exceptiononfail=True):
        # FIXME what about network errors!!!
        header = {'Content-Type': 'application/json'}
        data = json.dumps(data) if data else None
        fp = urllib2.urlopen(urllib2.Request(url, data, header))
        payload = json.loads(fp.read())
        fp.close()
        self._last_connected = time.time()
        if payload["status"] == "fail" and exceptiononfail:
            raise Exception("Chromanode error: %s!" % payload['data']['type'])
        return payload.get("data")

    def get_merkle(self, txid):
        url = "%s/v1/transactions/merkle?txid=%s" % (self.baseurl, txid)
        result = self._query(url)
        return {
            "merkle": result["block"]["merkle"],
            "block_height": result["block"]["height"],
            "pos": result["block"]["index"]
        }

    def get_raw(self, txid):
        """ Return rawtx for given txid. """
        if txid in self._cache_rawtx:
            return self._cache_rawtx[txid]
        url = "%s/v1/transactions/raw?txid=%s" % (self.baseurl, txid)
        rawtx = self._query(url)["hex"]
        self._cache_rawtx[txid] = rawtx
        return rawtx

    def get_tx_blockhash(self, txid):
        """ Return blockid for given txid. """
        url = "%s/v1/transactions/merkle?txid=%s" % (self.baseurl, txid)
        result = self._query(url, exceptiononfail=False)
        # errors
        if 'source' not in result:
            if result['type'] == 'TxNotFound':
                return None, False
            else:
                msg = "Error getting tx blockhash '%s'!" % result["type"]
                raise Exception(msg)

        if result["source"] == "mempool":  # unconfirmed
            return None, True
        return result["block"]["hash"], True

    def get_block_height(self, blockid):
        """ Return blockheight for given blockid. """
        url = "%s/v1/headers/query?from=%s&count=1" % (self.baseurl, blockid)
        result = self._query(url)
        return result["from"]

    def get_tx_height(self, txid):
        blockid = self.get_tx_blockhash(txid)[0]
        return self.get_block_height(blockid)

    def get_header(self, blockheight):
        """ Return header for given blockheight.
        Header format: {
            'version':         int,
            'prev_block_hash': hash,
            'merkle_root':     hast,
            'timestamp':       int,
            'bits':            int,
            'nonce':           int,
        }
        """
        header = self.read_header(blockheight)
        header['block_height'] = blockheight
        return header

    def read_raw_header(self, blockheight):
        """ Return rawheader for given blockheight. """
        urlargs = (self.baseurl, blockheight)
        url = "%s/v1/headers/query?from=%s&count=1" % urlargs
        return self._query(url)["headers"]

    def get_address_history(self, address):
        """ Return list of txids where address was used. """
        url = "%s/v1/addresses/query?addresses=%s" % (self.baseurl, address)
        result = self._query(url)
        txids = [entry["txid"] for entry in result["transactions"]]
        self._cache_currentheight = result['latest']['height']
        return txids

    def get_height(self):
        """ Return current blockchain height. """
        return self._cache_currentheight

    def get_block_count(self):
        """ Return current block count. """
        return self.get_height()

    def publish_tx(self, rawtx):
        """ Publish rawtx on bitcoin network and return txid. """
        url = "%s/v1/transactions/send" % self.baseurl
        self._query(url, {"rawtx": rawtx})
        return Tx.tx_from_hex(rawtx).id()

    def get_utxo(self, address):
        """ Return list of txids with utxos for the given address. """
        urlargs = (self.baseurl, address)
        url = "%s/v1/addresses/query?addresses=%s&status=unspent" % urlargs
        result = self._query(url)
        txids = [entry["txid"] for entry in result["transactions"]]
        self._cache_currentheight = result['latest']['height']
        return txids

    def get_chunk(self, index, chunksize=2016):
        urlargs = (self.baseurl, index * chunksize, chunksize)
        url = "%s/v1/headers/query?from=%s&count=%s" % urlargs
        result = self._query(url)
        return result["headers"]
