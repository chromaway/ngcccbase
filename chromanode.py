#!/usr/bin/env python
import os, sys
import json

import web

from coloredcoinlib import BlockchainState, ColorDefinition

urls = (
    '/tx', 'Tx',
    '/publish_tx', 'PublishTx',
    '/tx_blockhash', 'TxBlockhash',
    '/prefetch', 'Prefetch',
    '/blockcount', 'BlockCount',
    '/block', 'Block',
    '/chunk', 'Chunk'
)

testnet = False
if (len(sys.argv) > 3) and (sys.argv[3] == 'testnet'):
    testnet = True

CHUNKS_PATH = os.path.join('chromanode', 'testnet') if testnet else 'chromanode'
if len(sys.argv) > 2:
    CHUNKS_PATH = os.path.join(sys.argv[2], 'testnet') if testnet else sys.argv[2]
if not os.path.exists(CHUNKS_PATH):
    os.makedirs(CHUNKS_PATH)

blockchainstate = BlockchainState.from_url(None, testnet)


class ErrorThrowingRequestProcessor:
    def require(self, data, key, message):
        value = data.get(key, None)
        if value is None:
            raise web.HTTPError("400 Bad request", 
                                {"content-type": "text/plain"},
                                message)


class Tx(ErrorThrowingRequestProcessor):
    def POST(self):
        # data is sent in as json
        data = json.loads(web.data())
        self.require(data, 'txhash', "TX requires txhash")
        txhash = data.get('txhash')
        print txhash
        return blockchainstate.get_raw(txhash)


class PublishTx(ErrorThrowingRequestProcessor):
    def POST(self):
        txdata = web.data()
        reply = None
        try:
            reply = blockchainstate.bitcoind.sendrawtransaction(txdata)
        except Exception as e:
            reply = ("Error: " + str(e))
        return reply


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


class BlockCount(ErrorThrowingRequestProcessor):
    def GET(self):
        return str(blockchainstate.get_block_count())


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        import decimal
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


class Block(ErrorThrowingRequestProcessor):
    def POST(self):
        data = json.loads(web.data())
        self.require(data, 'id', "Block requires id (block number or block hash)")
        id = data.get('id')
        blockhash = id if type(id) == str else blockchainstate.get_block_hash(id)
        return json.dumps(blockchainstate.get_block(blockhash), cls=DecimalEncoder)


class Chunk(ErrorThrowingRequestProcessor):
    _chunks = {}

    def _rev_hex(self, s):
        return s.decode('hex')[::-1].encode('hex')

    def _int_to_hex(self, i, length=1):
        s = hex(i)[2:].rstrip('L')
        s = "0"*(2*length - len(s)) + s
        return self._rev_hex(s)

    def _header_to_string(self, res):
        s = self._int_to_hex(res.get('version'),4) \
            + self._rev_hex(res.get('previousblockhash', "0"*64)) \
            + self._rev_hex(res.get('merkleroot')) \
            + self._int_to_hex(res.get('time'),4) \
            + self._rev_hex(res.get('bits')) \
            + self._int_to_hex(res.get('nonce'),4)
        return s

    def _get_chunk(self, index):
        chunks = self.__class__._chunks
        if index in chunks:
            return chunks[index]

        chunk_path = os.path.join(os.path.join(CHUNKS_PATH, str(index)))
        if os.path.exists(chunk_path):
            chunks[index] = open(chunk_path, 'r').read()
            return self._get_chunk(index)

        headers = ''
        blockhash = blockchainstate.get_block_hash(index*2016)
        while len(headers) != 2016*80:
            block = blockchainstate.get_block(blockhash)
            headers += self._header_to_string(block).decode('hex')
            blockhash = block['nextblockhash']

        open(chunk_path, 'w').write(headers)
        return self._get_chunk(index)

    def POST(self):
        data = json.loads(web.data())
        self.require(data, 'index', "Chunk requires index")
        index = data.get('index')
        max_index = (blockchainstate.get_block_count() + 1)/2016
        if max_index < index:
            return ''
        return self._get_chunk(index)


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
