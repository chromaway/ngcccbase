#!/usr/bin/env python

import json
import sys
import web

from coloredcoinlib import BlockchainState, ColorDefinition


blockchainstate = BlockchainState.from_url(None, True)

urls = (
    '/tx', 'Tx',
    '/prefetch', 'Prefetch',
)


class ErrorThrowingRequestProcessor:
    def require(self, data, key, message):
        value = data.get(key)
        if not value:
            raise web.HTTPError("400 Bad request", 
                                {"content-type": "text/plain"},
                                message)


class Tx(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.input().keys()[0])
        self.require(data, 'txhash', "TX requires txhash")
        txhash = data.get('txhash')
        return blockchainstate.get_raw(txhash)


class Prefetch(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.input().keys()[0])
        self.require(data, 'txhash', "Prefetch requires txhash")
        self.require(data, 'output_set', "Prefetch requires output_set")
        self.require(data, 'color_desc', "Prefetch requires color_desc")
        txhash = data.get('txhash')
        output_set = data.get('output_set')
        color_desc = data.get('color_desc')
        limit = data.get('limit')
        color_def = ColorDefinition.from_color_desc(17, color_desc)

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
    app = web.application(urls, globals())
    app.run()
