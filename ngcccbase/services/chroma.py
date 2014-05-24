#!/usr/bin/env python

"""
chroma.py

This is a connector to chromawallet's servers to grab transaction details
"""

import bitcoin
import json
import urllib2


from coloredcoinlib import CTransaction, BlockchainStateBase


class UnimplementedError(RuntimeError):
    pass


class ChromaBlockchainState(BlockchainStateBase):

    tx_lookup = {}

    def __init__(self, url_stem="http://localhost:28832", testnet=False):
        """Initialization takes the url and port of the chroma server.
        We have to use the chroma server for everything that we would
        use 
        We use the normal bitcoind interface, except for
        get_raw_transaction, where we have to do separate lookups
        to blockchain and electrum.
        """
        self.url_stem = url_stem

    def publish_tx(self, txdata):
        url = "%s/publish_tx" % self.url_stem
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
        url = "%s/prefetch" % self.url_stem
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
        url = "%s/tx_blockhash" % self.url_stem
        data = {'txhash': txhash}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        payload = f.read()
        f.close()
        data = json.loads(payload)
        return data[0], data[1]

    def get_block_count(self):
        url = "%s/blockcount" % self.url_stem
        data = urllib2.urlopen(url).read()
        return int(data)

    def get_height(self):
        return self.get_block_count()

    def get_block_height(self, block_hash):
        url = "%s/header" % self.url_stem
        data = json.dumps({
            'block_hash': block_hash,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())['block_height']        

    def get_header(self, height):
        url = "%s/header" % self.url_stem
        data = json.dumps({
            'height': height,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return json.loads(req.read())

    def get_chunk(self, index):
        url = "%s/chunk" % self.url_stem
        data = json.dumps({
            'index': index,
        })
        req = urllib2.urlopen(urllib2.Request(url,
            data, {'Content-Type': 'application/json'}))
        return req.read().encode('hex')

    def get_merkle(self, txhash):
        url = "%s/merkle" % self.url_stem
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
        url = "%s/tx" % self.url_stem
        data = {'txhash': txhash}
        req = urllib2.Request(url, json.dumps(data),
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        payload = f.read()
        self.tx_lookup[txhash] = payload
        f.close()
        return payload

    def get_tx(self, txhash):
        txhex = self.get_raw(txhash)
        txbin = bitcoin.core.x(txhex)
        tx = bitcoin.core.CTransaction.deserialize(txbin)
        return CTransaction.from_bitcoincore(txhash, tx, self)

    def get_mempool_txs(self):
        return []

