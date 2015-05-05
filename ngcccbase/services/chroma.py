#!/usr/bin/env python

"""
chroma.py

This is a connector to chromawallet's servers to grab transaction details
"""

import bitcoin
import json
import urllib2
from pycoin.tx.Tx import Tx
from ngcccbase.blockchain import BaseStore
from coloredcoinlib import CTransaction, BlockchainStateBase


class AbstractChromanodeBlockchainState(BlockchainStateBase):

    def connected(self): # FIXME have ChromanodeInterface manage this smartly
        try:
          return bool(self.get_block_count())
        except:
          return False

    def get_tx(self, txhash):
        txhex = self.get_raw(txhash)
        txbin = bitcoin.core.x(txhex)
        tx = bitcoin.core.CTransaction.deserialize(txbin)
        return CTransaction.from_bitcoincore(txhash, tx, self)


class ChromanodeInterface(AbstractChromanodeBlockchainState, BaseStore):

    def __init__(self, baseurl=None, testnet=False, cache_minconfirms=6):
        testnet_baseurl = "http://v1.testnet.bitcoin.chromanode.net"
        mainnet_baseurl = "http://v1.livenet.bitcoin.chromanode.net"
        self.testnet = testnet
        if baseurl:
           self.baseurl = baseurl
        else:
           self.baseurl = testnet_baseurl if testnet else mainnet_baseurl

        # init caches
        self.cache_minconfirms = cache_minconfirms
        self.cache_rawtx = {} # txid -> rawtx
        self.cache_txblockhash = {} # txid -> blockhash
        self.cache_rawheaders = {} # blockheight -> rawheader
        self.cache_blockheight = {} # blockhash -> blockheight

    def _cancache(self, blockheight):
        currentheight = self.get_block_count()
        return (currentheight - blockheight) >= self.cache_minconfirms

    def _query(self, url, data=None):
        header = {'Content-Type': 'application/json'}
        data = json.dumps(data) if data else None
        fp = urllib2.urlopen(urllib2.Request(url, data, header))
        payload = json.loads(fp.read())
        fp.close()
        if payload["status"] == "fail":
            raise Exception("Chromanode error: %s!" % payload['data']['type'])
        return payload.get("data")

    def get_raw(self, txid):
        """ Return rawtx for given txid. """

        # get from cache
        cachedrawtx = self.cache_rawtx.get(txid)
        if cachedrawtx:
            return cachedrawtx

        # get from chromanode
        url = "%s/v1/transactions/raw?txid=%s" % (self.baseurl, txid)
        rawtx = self._query(url)["hex"]

        # add to cache
        self.cache_rawtx[txid] = rawtx
        return rawtx

    def get_tx_blockhash(self, txid):
        """ Return blockhash for given txid. """

        # get from cache
        blockhash = self.cache_txblockhash.get(txid)
        if blockhash:
          return blockhash

        # get from chromanode
        url = "%s/v1/transactions/merkle?txid=%s" % (self.baseurl, txid)
        result = self._query(url)
        if result["source"] == "mempool": # unconfirmed
            return None, True

        # add to cache
        blockhash = result["block"]["hash"]
        blockheight = result["block"]["height"]
        if self._cancache(blockheight):
            self.cache_txblockhash[txid] = blockhash
            self.cache_blockheight[blockhash] = blockheight
        return blockhash, True

    def get_block_height(self, blockhash):
        """ Return blockheight for given blockhash. """
        
        # get from cache
        blockheight = self.cache_blockheight.get(blockhash)
        if blockheight:
          return blockheight

        # get from chromanode
        url = "%s/v1/headers/query?from=%s&count=1" % (self.baseurl, blockhash)
        result = self._query(url)
        blockheight = result["from"]

        # add to cache
        if self._cancache(blockheight):
            self.cache_blockheight[blockhash] = blockheight
            self.cache_rawheaders[blockheight] = result["headers"]
        return blockheight

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
        rawheader = self.cache_rawheaders.get(blockheight)
        if rawheader:
            return rawheader

        # get from chromanode
        url = "%s/v1/headers/query?from=%s&count=1" % (self.baseurl, blockheight)
        result = self._query(url)
        rawheader = result["headers"]

        # add to cache
        if self._cancache(blockheight):
            self.cache_rawheaders[blockheight] = rawheader
        return rawheader

    def get_address_history(self, address): 
        """ TODO docstring """
        # TODO only query if blocks added since last query
        url = "%s/v1/addresses/query?addresses=%s" % (self.baseurl, address)
        history = self._query(url)["transactions"]
        return [entry["txid"] for entry in history]

    def get_block_count(self): 
        """ TODO docstring """
        # TODO only get on startup and update on newBlock notification
        url = "%s/v1/headers/latest" % self.baseurl
        return self._query(url)["height"]

    def publish_tx(self, rawtx):
        """ TODO docstring """
        url = "%s/v1/transactions/send" % self.baseurl
        self._query(url, { "rawtx" : rawtx })
        return Tx.tx_from_hex(rawtx).id()

    def get_utxo(self, address):
        """ TODO docstring """
        # TODO only query if blocks added since last query
        urlargs = (self.baseurl, address)
        url = "%s/v1/addresses/query?addresses=%s&status=unspent" % urlargs
        history = self._query(url)["transactions"]
        return [[entry["txid"], None, None, None] for entry in history]


class ChromaBlockchainState(AbstractChromanodeBlockchainState):


    def __init__(self, baseurl="http://localhost:28832", testnet=False):
        """Initialization takes the url and port of the chroma server.
        We have to use the chroma server for everything that we would
        use
        We use the normal bitcoind interface, except for
        get_raw_transaction, where we have to do separate lookups
        to blockchain and electrum.
        """
        self.baseurl = baseurl

    def publish_tx(self, txdata):
        url = "%s/publish_tx" % self.baseurl
        req = urllib2.Request(url, txdata,
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        reply = f.read()
        f.close()
        if reply[0] == 'E' or (len(reply) != 64):
            raise Exception(reply)
        else:
            return reply

    def prefetch(self, txhash, output_set, color_desc, limit):
        url = "%s/prefetch" % self.baseurl
        data = {'txhash': txhash, 'output_set': output_set,
                'color_desc': color_desc, 'limit': limit}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        txs = json.loads(f.read())
        for txhash, txraw in txs.items():
            self.tx_lookup[txhash] = txraw
        f.close()
        return

    def get_tx_blockhash(self, txhash):
        url = "%s/tx_blockhash" % self.baseurl
        data = {'txhash': txhash}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        payload = f.read()
        f.close()
        data = json.loads(payload)
        return data[0], data[1]

    def get_block_count(self):
        url = "%s/blockcount" % self.baseurl
        data = urllib2.urlopen(url).read()
        return int(data)

    def get_height(self):
        return self.get_block_count()

    def get_block_height(self, block_hash):
        url = "%s/header" % self.baseurl
        data = json.dumps({
            'block_hash': block_hash,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())['block_height']

    def get_header(self, height):
        url = "%s/header" % self.baseurl
        data = json.dumps({
            'height': height,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())

    def get_chunk(self, index):
        url = "%s/chunk" % self.baseurl
        data = json.dumps({
            'index': index,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return req.read().encode('hex')

    def get_merkle(self, txhash):
        url = "%s/merkle" % self.baseurl
        data = json.dumps({
            'txhash': txhash,
            'blockhash': self.get_tx_blockhash(txhash)[0],
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())

    def get_raw(self, txhash):
        if self.tx_lookup.get(txhash):
            return self.tx_lookup[txhash]
        url = "%s/tx" % self.baseurl
        data = {'txhash': txhash}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        payload = f.read()
        self.tx_lookup[txhash] = payload
        f.close()
        return payload

    def get_mempool_txs(self):
        return []

