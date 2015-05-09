#!/usr/bin/env python

import bitcoin
import json
import urllib2
from pycoin.tx.Tx import Tx
from ngcccbase.blockchain import BaseStore
from coloredcoinlib import CTransaction, BlockchainStateBase
from socketIO_client import SocketIO, LoggingNamespace



class ChromanodeInterface(BlockchainStateBase, BaseStore):
    # TODO docstring

    def __init__(self, baseurl=None, testnet=False, cache_minconfirms=6):
        # TODO docstring

        # init baseurl
        testnet_baseurl = "http://v1.testnet.bitcoin.chromanode.net"
        mainnet_baseurl = "http://v1.livenet.bitcoin.chromanode.net"
        if baseurl:
           self.baseurl = baseurl
        else:
           self.baseurl = testnet_baseurl if testnet else mainnet_baseurl

        # init caches
        self._cache_currentheight = 0
        self._cache_minconfirms = cache_minconfirms
        self._cache_rawtx = {}          # txid -> rawtx
        self._cache_txblockid = {}      # txid -> blockid
        self._cache_rawheaders = {}     # blockheight -> rawheader
        self._cache_blockheight = {}    # blockid -> blockheight
        self._cache_addresshistory = {} # address -> [txids]
        self._cache_addressutxo = {}    # address -> [txids]

        # init notifications
        self._notification_init()

        # init _cache_currentheight
        queryurl = "%s/v1/headers/latest" % self.baseurl
        self._update_cache_currentheight(self._query(queryurl)["height"])

    def _notification_init(self):
        # FIXME confirm this works!
        self._socketIO = SocketIO(self.baseurl, 80, LoggingNamespace)
        self._socketIO.emit('subscribe', 'new-block', self._on_newblock)
        self._socketIO.wait(seconds=1)

    def _update_cache_currentheight(self, currentheight):
        if currentheight != self._cache_currentheight:
            self._cache_addresshistory = {} # clear in case of orphaned blocks
            self._cache_addressutxo = {} # clear in case of orphaned blocks
            self._cache_currentheight = currentheight

    def _on_newblock(self, blockhash, blockheight):
        print '_on_newblock', blockhash, blockheight
        self._update_cache_currentheight(blockheight)

    def _cancache(self, blockheight):
        return (self.get_block_count() - blockheight) >= self._cache_minconfirms

    def _query(self, url, data=None):
        header = {'Content-Type': 'application/json'}
        data = json.dumps(data) if data else None
        fp = urllib2.urlopen(urllib2.Request(url, data, header))
        payload = json.loads(fp.read())
        fp.close()
        if payload["status"] == "fail":
            raise Exception("Chromanode error: %s!" % payload['data']['type'])
        return payload.get("data")

    def connected(self):
        return self._socketIO.connected

    def get_raw(self, txid):
        """ Return rawtx for given txid. """

        # get from cache
        cachedrawtx = self._cache_rawtx.get(txid)
        if cachedrawtx:
            return cachedrawtx

        # get from chromanode
        url = "%s/v1/transactions/raw?txid=%s" % (self.baseurl, txid)
        rawtx = self._query(url)["hex"]

        # add to cache
        self._cache_rawtx[txid] = rawtx
        return rawtx

    def get_tx_blockhash(self, txid): # FIXME remove unneeded bool return value
        """ Return blockid for given txid. """

        # get from cache
        blockid = self._cache_txblockid.get(txid)
        if blockid:
          return blockid, True

        # get from chromanode
        url = "%s/v1/transactions/merkle?txid=%s" % (self.baseurl, txid)
        result = self._query(url)
        if result["source"] == "mempool": # unconfirmed
            return None, True

        # add to cache
        blockid = result["block"]["hash"]
        blockheight = result["block"]["height"]
        if self._cancache(blockheight):
            self._cache_txblockid[txid] = blockid
            self._cache_blockheight[blockid] = blockheight
        return blockid, True

    def get_block_height(self, blockid):
        """ Return blockheight for given blockid. """
        
        # get from cache
        blockheight = self._cache_blockheight.get(blockid)
        if blockheight:
          return blockheight

        # get from chromanode
        url = "%s/v1/headers/query?from=%s&count=1" % (self.baseurl, blockid)
        result = self._query(url)
        blockheight = result["from"]

        # add to cache
        if self._cancache(blockheight):
            self._cache_blockheight[blockid] = blockheight
            self._cache_rawheaders[blockheight] = result["headers"]
        return blockheight

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
        return self.read_header(blockheight)

    def read_raw_header(self, blockheight):
        """ Return rawheader for given blockheight. """
        
        # get from cache
        rawheader = self._cache_rawheaders.get(blockheight)
        if rawheader:
            return rawheader

        # get from chromanode
        url = "%s/v1/headers/query?from=%s&count=1" % (self.baseurl, blockheight)
        rawheader = self._query(url)["headers"]

        # add to cache
        if self._cancache(blockheight):
            self._cache_rawheaders[blockheight] = rawheader
        return rawheader

    def get_address_history(self, address): 
        """ Return list of txids where address was used. """

        # get from cache
        txids = self._cache_addresshistory.get(address)
        if txids:
            return txids

        # get from chromanode
        url = "%s/v1/addresses/query?addresses=%s" % (self.baseurl, address)
        result = self._query(url)
        txids = [entry["txid"] for entry in result["transactions"]]

        # add to cache
        self._update_cache_currentheight(result['latest']['height'])
        self._cache_addresshistory[address] = txids 
        return txids

    def get_block_count(self): 
        """ Return current blockchain height. """
        return self._cache_currentheight

    def publish_tx(self, rawtx):
        """ Publish rawtx on bitcoin network and return txid. """

        # publish
        url = "%s/v1/transactions/send" % self.baseurl
        self._query(url, { "rawtx" : rawtx })
        txid = Tx.tx_from_hex(rawtx).id()

        # clear caches possibly invalid caches
        self._cache_addresshistory = {} # TODO only clear affected addresses
        self._cache_addressutxo = {} # TODO only clear affected addresses
        return txid

    def get_utxo(self, address):
        """ Return list of txids with utxos for the given address. """

        # get from cache
        txids = self._cache_addressutxo.get(address)
        if txids:
            return txids

        # get from chromanode
        urlargs = (self.baseurl, address)
        url = "%s/v1/addresses/query?addresses=%s&status=unspent" % urlargs
        result = self._query(url)
        txids = [entry["txid"] for entry in result["transactions"]]

        # add to cache
        self._update_cache_currentheight(result['latest']['height'])
        self._cache_addressutxo[address] = txids 
        return txids


