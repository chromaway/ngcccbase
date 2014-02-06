#!/usr/bin/env python

"""
chroma.py

This is a connector to chromawallet's servers to grab transaction details
"""

import bitcoin
import json
import urllib2

from coloredcoinlib.blockchain import CTransaction


class UnimplementedError(RuntimeError):
    pass


class ChromaBlockchainState:

    tx_lookup = {}

    @classmethod
    def from_url(cls, url, testnet=False):
        return cls()

    def __init__(self, url="localhost", port=28832):
        """Initialization takes the url and port of the chroma server.
        We have to use the chroma server for everything that we would
        use 
        We use the normal bitcoind interface, except for
        get_raw_transaction, where we have to do separate lookups
        to blockchain and electrum.
        """
        self.url_stem = "http://%s:%s" % (url, port)

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

