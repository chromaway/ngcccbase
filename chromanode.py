#!/usr/bin/env python
import os, sys
import json
import hashlib
import threading, time

import web

from coloredcoinlib import BlockchainState, ColorDefinition


urls = (
    '/tx', 'Tx',
    '/publish_tx', 'PublishTx',
    '/tx_blockhash', 'TxBlockhash',
    '/prefetch', 'Prefetch',
    '/blockcount', 'BlockCount',
    '/header', 'Header',
    '/chunk', 'Chunk',
    '/merkle', 'Merkle'
)

testnet = False
if (len(sys.argv) > 2) and (sys.argv[2] == 'testnet'):
    testnet = True

HEADERS_FILE = 'headers.testnet' if testnet else 'headers.mainnet'
if (len(sys.argv) > 3):
    HEADERS_FILE = sys.argv[3]

blockchainstate = BlockchainState.from_url(None, testnet)

my_lock = threading.RLock()
def call_synchronized(f):
    def newFunction(*args, **kw):
        with my_lock:
            return f(*args, **kw)
    return newFunction

blockchainstate.bitcoind._call = call_synchronized(
    blockchainstate.bitcoind._call)
blockchainstate.bitcoind._batch = call_synchronized(
    blockchainstate.bitcoind._batch)

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


class Header(ErrorThrowingRequestProcessor):
    def POST(self):
        data = json.loads(web.data())
        block_hash = data.get('block_hash')
        if not block_hash:
            self.require(data, 'height', "block_hash or height required")
            height = data.get('height')
            block_hash = blockchainstate.get_block_hash(height)
        block = blockchainstate.get_block(block_hash)
        return json.dumps({
            'block_height':    block['height'],
            'version':         block['version'],
            'prev_block_hash': block['previousblockhash'],
            'merkle_root':     block['merkleroot'],
            'timestamp':       block['time'],
            'bits':            int(block['bits'], 16),
            'nonce':           block['nonce'],
        }, cls=DecimalEncoder)


class ChunkThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.running = False
        self.lock = threading.Lock()
        self.blockchainstate = BlockchainState.from_url(None, testnet)
        self.headers = ''

    def is_running(self):
        with self.lock:
            return self.running

    def stop(self):
        with self.lock:
            self.running = False

    def run(self):
        self.headers = open(HEADERS_FILE, 'ab+').read()

        with self.lock:
            self.running = True

        run_time = time.time()
        while self.is_running():
            if run_time > time.time():
                time.sleep(0.05)
                continue
            run_time = time.time() + 1

            height = self.blockchainstate.get_block_count()
            if height == self.height:
                continue
            if height < self.height:
                self.headers = self.headers[:height*80]
            while height > self.height:
                if not self.is_running():
                    break
                block_height = self.height + 1
                blockhash = self.blockchainstate.get_block_hash(block_height)
                block = self.blockchainstate.get_block(blockhash)

                if block_height == 0:
                    self.headers = self._header_to_string(block)
                else:
                    prev_hash = self._hash_header(self.headers[-80:])
                    if prev_hash == block['previousblockhash']:
                        self.headers += self._header_to_string(block)
                    else:
                        self.headers = self.headers[:-80]
            open(HEADERS_FILE, 'wb').write(self.headers)

    @property
    def height(self):
        return len(self.headers)/80 - 1

    def _rev_hex(self, s):
        return s.decode('hex')[::-1].encode('hex')

    def _int_to_hex(self, i, length=1):
        s = hex(i)[2:].rstrip('L')
        s = "0"*(2*length - len(s)) + s
        return self._rev_hex(s)

    def _header_to_string(self, h):
        s = self._int_to_hex(h.get('version'),4) \
            + self._rev_hex(h.get('previousblockhash', "0"*64)) \
            + self._rev_hex(h.get('merkleroot')) \
            + self._int_to_hex(h.get('time'),4) \
            + self._rev_hex(h.get('bits')) \
            + self._int_to_hex(h.get('nonce'),4)
        return s.decode('hex')

    def _hash_header(self, raw_header):
        return hashlib.sha256(hashlib.sha256(raw_header).digest()).digest()[::-1].encode('hex_codec')

chunkThread = ChunkThread()


class Chunk(ErrorThrowingRequestProcessor):
    def POST(self):
        data = json.loads(web.data())
        self.require(data, 'index', "Chunk requires index")
        index = data.get('index')
        with open(HEADERS_FILE, 'rb') as headers:
            headers.seek(index*2016*80)
            return headers.read(2016*80)


class Merkle(ErrorThrowingRequestProcessor):
    def POST(self):
        data = json.loads(web.data())
        self.require(data, 'txhash', "Merkle requires txhash")
        self.require(data, 'blockhash', "Merkle requires blockhash")
        txhash = data.get('txhash')
        blockhash = data.get('blockhash')

        hash_decode = lambda x: x.decode('hex')[::-1]
        hash_encode = lambda x: x[::-1].encode('hex')
        Hash = lambda x: hashlib.sha256(hashlib.sha256(x).digest()).digest()

        b = blockchainstate.get_block(blockhash)
        tx_list = b.get('tx')
        tx_pos = tx_list.index(txhash)

        merkle = map(hash_decode, tx_list)
        target_hash = hash_decode(txhash)
        s = []
        while len(merkle) != 1:
            if len(merkle) % 2:
                merkle.append(merkle[-1])
            n = []
            while merkle:
                new_hash = Hash(merkle[0] + merkle[1])
                if merkle[0] == target_hash:
                    s.append(hash_encode(merkle[1]))
                    target_hash = new_hash
                elif merkle[1] == target_hash:
                    s.append(hash_encode(merkle[0]))
                    target_hash = new_hash
                n.append(new_hash)
                merkle = merkle[2:]
            merkle = n

        return json.dumps({"block_height": b.get('height'), "merkle": s, "pos": tx_pos})


if __name__ == "__main__":
    import signal
    def sigint_handler(signum, frame):
        print ('exit chunk thread')
        chunkThread.stop()
        print ('done')
        sys.exit(1)
    signal.signal(signal.SIGINT, sigint_handler)

    chunkThread.start()

    app = web.application(urls, globals())
    app.run()
