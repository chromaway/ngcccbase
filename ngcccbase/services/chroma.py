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

    def __init__(self, baseurl=None, testnet=False):
        testnet_baseurl = "http://v1.testnet.bitcoin.chromanode.net"
        mainnet_baseurl = "http://v1.livenet.bitcoin.chromanode.net"
        self.testnet = testnet
        if baseurl:
           self.baseurl = baseurl
        else:
           self.baseurl = testnet_baseurl if testnet else mainnet_baseurl

    def _chromanode(self, url, data=None):
        header = {'Content-Type': 'application/json'}
        data = json.dumps(data) if data else None
        fp = urllib2.urlopen(urllib2.Request(url, data, header))
        payload = json.loads(fp.read())
        fp.close()
        if payload["status"] == "fail":
            raise Exception("Chromanode error: %s!" % payload['data']['type'])
        return payload.get("data")

    def get_raw(self, txid): # TODO add cache
        url = "%s/v1/transactions/raw?txid=%s" % (self.baseurl, txid)
        return self._chromanode(url)["hex"]

    def get_tx_blockhash(self, txid): # TODO add cache (only confirmed >= 6)
        url = "%s/v1/transactions/merkle?txid=%s" % (self.baseurl, txid)
        result = self._chromanode(url)
        if result["source"] == "mempool": # unconfirmed
            return None, True
        return result["block"]["hash"], True

    def get_block_height(self, blockid): # TODO add cache (only confirmed >= 6)
        url = "%s/v1/headers/query?from=%s&count=1" % (self.baseurl, blockid)
        return self._chromanode(url)["from"]

    def get_header(self, height): # TODO add cache (only confirmed >= 6)
        return self.read_header(height)

    def read_raw_header(self, height):
        url = "%s/v1/headers/query?from=%s&count=1" % (self.baseurl, height)
        return self._chromanode(url)["headers"]

    def get_address_history(self, address):
        url = "%s/v1/addresses/query?addresses=%s" % (self.baseurl, address)
        history = self._chromanode(url)["transactions"]
        return [entry["txid"] for entry in history]

    def get_block_count(self):
        url = "%s/v1/headers/latest" % self.baseurl
        return self._chromanode(url)["height"]

    def publish_tx(self, rawtx):
        url = "%s/v1/transactions/send" % self.baseurl
        self._chromanode(url, { "rawtx" : rawtx })
        return Tx.tx_from_hex(rawtx).id()

    def get_utxo(self, address):
        urlargs = (self.baseurl, address)
        url = "%s/v1/addresses/query?addresses=%s&status=unspent" % urlargs
        history = self._chromanode(url)["transactions"]
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

