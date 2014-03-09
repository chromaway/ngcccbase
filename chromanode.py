#!/usr/bin/env python

import json
import sys
import web

from coloredcoinlib import BlockchainState, ColorDefinition

urls = (
    '/tx', 'Tx',
    '/publish_tx', 'PublishTx',
    '/tx_blockhash', 'TxBlockhash',
    '/prefetch', 'Prefetch',
    '/blockcount', 'BlockCount'
)

blockchainstate = None


class ErrorThrowingRequestProcessor:
    def require(self, data, key, message):
        value = data.get(key)
        if not value:
            raise web.HTTPError("400 Bad request", 
                                {"content-type": "text/plain"},
                                message)


class PublishTx(ErrorThrowingRequestProcessor):
    def POST(self):
        txdata = web.data()
        reply = None
        try:
            reply = blockchainstate.bitcoind.sendrawtransaction(txdata)
        except Exception as e:
            reply = ("Error: " + str(e))
        return reply

class BlockCount(ErrorThrowingRequestProcessor):
    def GET(self):
        return str(blockchainstate.get_block_count())

class Tx(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "TX requires txhash")
        txhash = data.get('txhash')
        print txhash
        return blockchainstate.get_raw(txhash)

class TxBlockhash(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "TX requires txhash")
        txhash = data.get('txhash')
        print txhash
        blockhash, in_mempool = blockchainstate.get_tx_blockhash(txhash)
        return json.dumps([blockhash, in_mempool])

class Prefetch(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "Prefetch requires txhash")
        self.require(data, 'output_set', "Prefetch requires output_set")
        self.require(data, 'color_desc', "Prefetch requires color_desc")
        txhash = data.get('txhash')
        output_set = data.get('output_set')
        color_desc = data.get('color_desc')
        limit = data.get('limit')

        # note the id doesn't actually matter we need to add it so
        #  we have a valid color definition
        color_def = ColorDefinition.from_color_desc(9999, color_desc)

        # gather all the transactions and return them
        tx_lookup = {}

        def process(current_txhash, current_outindex):
            """For any tx out, process the colorvalues of the affecting
            inputs first and then scan that tx.
            """
            if limit and len(tx_lookup) > limit:
                return
            if tx_lookup.get(current_txhash):
                return
            current_tx = blockchainstate.get_tx(current_txhash)
            if not current_tx:
                return
            tx_lookup[current_txhash] = blockchainstate.get_raw(current_txhash)

            # note a genesis tx will simply have 0 affecting inputs
            inputs = set()
            inputs = inputs.union(
                color_def.get_affecting_inputs(current_tx,
                                               [current_outindex]))
            for i in inputs:
                process(i.prevout.hash, i.prevout.n)

        for oi in output_set:
            process(txhash, oi)
        return tx_lookup


if __name__ == "__main__":
    testnet = False
    if (len(sys.argv) > 2) and (sys.args[2] == 'testnet'):
        testnet = True
    blockchainstate = BlockchainState.from_url(None, testnet)
    app = web.application(urls, globals())
    app.run()
