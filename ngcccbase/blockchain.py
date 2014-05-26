import os, sys, threading, Queue, time
import traceback
import abc
import hashlib

from coloredcoinlib import BlockchainStateBase
from coloredcoinlib.store import DataStore


class BaseStore(object):
    __metaclass__ = abc.ABCMeta

    def _rev_hex(self, s):
        return s.decode('hex')[::-1].encode('hex')

    def _int_to_hex(self, i, length=1):
        s = hex(i)[2:].rstrip('L')
        s = "0"*(2*length - len(s)) + s
        return self._rev_hex(s)

    def header_to_raw(self, h):
        s = self._int_to_hex(h.get('version'),4) \
            + self._rev_hex(h.get('prev_block_hash', "0"*64)) \
            + self._rev_hex(h.get('merkle_root')) \
            + self._int_to_hex(int(h.get('timestamp')),4) \
            + self._int_to_hex(int(h.get('bits')),4) \
            + self._int_to_hex(int(h.get('nonce')),4)
        return s.decode('hex')

    def header_from_raw(self, s):
        hex_to_int = lambda s: int('0x' + s[::-1].encode('hex'), 16)
        hash_encode = lambda x: x[::-1].encode('hex')
        return {
            'version':         hex_to_int(s[0:4]),
            'prev_block_hash': hash_encode(s[4:36]),
            'merkle_root':     hash_encode(s[36:68]),
            'timestamp':       hex_to_int(s[68:72]),
            'bits':            hex_to_int(s[72:76]),
            'nonce':           hex_to_int(s[76:80]),
        }

    @abc.abstractmethod
    def read_raw_header(self, height):
        pass

    def read_header(self, height):
        data = self.read_raw_header(height)
        if data is not None:
            return self.header_from_raw(data)
        return None


class FileStore(BaseStore):
    def __init__(self, path):
        self.path = path

    def get_height(self):
        try:
            return os.path.getsize(self.path)/80 - 1
        except OSError, e:
            return 0

    def read_raw_header(self, height):
        try:
            with open(self.path, 'rb') as store:
                store.seek(height*80)
                data = store.read(80)
                assert len(data) == 80
                return data
        except (OSError, AssertionError), e:
            return None

    def save_chunk(self, index, chunk):
        with open(self.path, 'ab+') as store:
            store.seek(index*2016*80)
            store.write(chunk)

    def save_chain(self, chain):
        with open(self.path, 'ab+') as store:
            for header in chain:
                store.seek(header['block_height']*80)
                store.write(self.header_to_raw(header))

    def truncate(self, index):
        with open(self.path, 'ab+') as store:
            store.seek(index*80)
            store.truncate()


class SQLStore(DataStore, BaseStore):
    _SQL_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS blockchain_headers (
    height INTEGER,
    version INTEGER,
    prev_block_hash VARCHAR(64),
    merkle_root VARCHAR(64),
    timestamp INTEGER,
    bits INTEGER,
    nonce INTEGER
);
"""

    _SQL_INDEX_HEIGHT = """\
CREATE UNIQUE INDEX IF NOT EXISTS blockchain_headers_height ON blockchain_headers (height);
"""
    _SQL_INDEX_PREV_BLOCK_HASH = """\
CREATE UNIQUE INDEX IF NOT EXISTS blockchain_headers_prev_block_hash ON blockchain_headers (prev_block_hash);
"""

    def __init__(self, conn):
        DataStore.__init__(self, conn)
        self.execute(self._SQL_CREATE_TABLE)
        self.execute(self._SQL_INDEX_HEIGHT)
        self.execute(self._SQL_INDEX_PREV_BLOCK_HASH)

    def get_height(self):
        return (self.execute("SELECT height FROM blockchain_headers ORDER BY height DESC LIMIT 1").fetchone() or [0])[0]

    def read_raw_header(self, height):
        header = self.read_header(height)
        return (None if header is None else self.header_to_raw(header))

    def read_header(self, height):
        data = self.execute("SELECT * FROM blockchain_headers WHERE height = ?",(height, )).fetchone()
        header = {
            'version': data[1],
            'prev_block_hash': data[2],
            'merkle_root': data[3],
            'timestamp': data[4],
            'bits': data[5],
            'nonce': data[6],
        }
        return header

    def _save_header(self, h):
        params = (h['block_height'], h['version'], h['prev_block_hash'], h['merkle_root'], h['timestamp'], h['bits'], h['nonce'])
        self.execute("""\
INSERT INTO blockchain_headers (
    height,
    version,
    prev_block_hash,
    merkle_root,
    timestamp,
    bits,
    nonce
) VALUES (?, ?, ?, ?, ?, ?, ?)""", params)

    def save_chunk(self, index, chunk):
        import time
        print time.time()
        chunk = chunk.encode('hex')
        for i in xrange(2016):
            header = self.header_from_raw(chunk[i*80:(i+1)*80])
            header['block_height'] = index*2016 + i
            self._save_header(header)
        print time.time()

    def save_chain(self, chain):
        pass

    def truncate(self, index):
        self.execute("""DELETE FROM blockchain_headers WHERE height >= ?""", (index,))


class NewBlocks(threading.Thread):
    def __init__(self, bcs, queue):
        threading.Thread.__init__(self)
        self.running = False
        self.lock = threading.Lock()
        self.daemon = True
        self.bcs = bcs
        self.queue = queue

    def run(self):
        with self.lock:
            self.running = True

        run_time = time.time()
        while self.is_running():
            if run_time > time.time():
                time.sleep(0.05)
                continue
            try:
                header = self.bcs.get_header(self.bcs.get_height())
                self.queue.put(header)
            except Exception, e:
                sys.stderr.write('Error! %s: %s\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
            run_time = time.time() + 30

    def is_running(self):
        with self.lock:
            return self.running

    def stop(self):
        with self.lock:
            self.running = False


class BlockHashingAlgorithm(object):
    max_bits = 0x1d00ffff
    max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000

    def __init__(self, store, testnet):
        self.store = store
        self.testnet = testnet

    def hash_header(self, raw_header):
        import hashlib
        return hashlib.sha256(hashlib.sha256(raw_header).digest()).digest()[::-1].encode('hex_codec')

    def get_target(self, index, chain=None):
        if chain is None:
            chain = []

        if index == 0:
            return self.max_bits, self.max_target

        first = self.store.read_header((index-1)*2016)
        last = self.store.read_header(index*2016-1)
        if last is None:
            for h in chain:
                if h.get('block_height') == index*2016-1:
                    last = h

        nActualTimespan = last.get('timestamp') - first.get('timestamp')
        nTargetTimespan = 14*24*60*60
        nActualTimespan = max(nActualTimespan, nTargetTimespan/4)
        nActualTimespan = min(nActualTimespan, nTargetTimespan*4)

        bits = last.get('bits')
        # convert to bignum
        MM = 256*256*256
        a = bits%MM
        if a < 0x8000:
            a *= 256
        target = (a) * pow(2, 8 * (bits/MM - 3))

        # new target
        new_target = min( self.max_target, (target * nActualTimespan)/nTargetTimespan )

        # convert it to bits
        c = ("%064X"%new_target)[2:]
        i = 31
        while c[0:2]=="00":
            c = c[2:]
            i -= 1

        c = int('0x'+c[0:6],16)
        if c > 0x800000: 
            c /= 256
            i += 1

        new_bits = c + MM * i
        return new_bits, new_target

    def verify_chunk(self, index, chunk):
        height = index*2016
        num = len(chunk)/80

        if index == 0:  
            prev_hash = ("0"*64)
        else:
            prev_header = self.store.read_header(index*2016-1)
            if prev_header is None:
                raise
            prev_hash = self.hash_header(self.store.header_to_raw(prev_header))

        bits, target = self.get_target(index)

        for i in range(num):
            raw_header = chunk[i*80:(i+1)*80]
            header = self.store.header_from_raw(raw_header)
            _hash = self.hash_header(raw_header)

            assert prev_hash == header.get('prev_block_hash')
            try:
                assert bits == header.get('bits')
                assert int('0x'+_hash, 16) < target
            except AssertionError:
                if self.testnet and header.get('timestamp') - prev_header.get('timestamp') > 1200:
                    assert self.max_bits == header.get('bits')
                    assert int('0x'+_hash, 16) < self.max_target
                else:
                    raise

            prev_header = header
            prev_hash = _hash

    def verify_chain(self, chain):
        prev_header = self.store.read_header(chain[0].get('block_height')-1)
        prev_hash = self.hash_header(self.store.header_to_raw(prev_header))

        for header in chain:
            bits, target = self.get_target(header.get('block_height')/2016, chain)
            _hash = self.hash_header(self.store.header_to_raw(header))

            assert prev_hash == header.get('prev_block_hash')
            try:
                assert bits == header.get('bits')
                assert int('0x'+_hash, 16) < target
            except AssertionError:
                if self.testnet and header.get('timestamp') - prev_header.get('timestamp') > 1200:
                    assert self.max_bits == header.get('bits')
                    assert int('0x'+_hash, 16) < self.max_target
                else:
                    raise

            prev_header = header
            prev_hash = _hash


class VerifiedBlockchainState(BlockchainStateBase, threading.Thread):
    def __init__(self, bcs, txdb, testnet, path):
        threading.Thread.__init__(self)
        self.running = False
        self.sync = False
        self.lock = threading.Lock()
        self.queue = Queue.Queue()
        self.newBlocks = NewBlocks(bcs, self.queue)

        self.bcs = bcs
        self.txdb = txdb
        self.store = FileStore(os.path.join(path, 'blockchain_headers'))
        self.bha = BlockHashingAlgorithm(self.store, testnet)

        self.local_height = 0
        self._set_local_height()
        self.daemon = True

    def run(self):
        with self.lock:
            self.running = True

        self.newBlocks.start()
        while self.is_running():
            try:
                header = self.queue.get_nowait()
            except Queue.Empty:
                time.sleep(0.05)
                continue

            if header['block_height'] == self.height:
                with self.lock:
                    self.sync = True
                continue

            try:
                with self.lock:
                    self.sync = False
                if -50 < header['block_height'] - self.height < 50:
                    retval = self._get_chain(header)
                else:
                    retval = self._get_chunks(header)
                with self.lock:
                    self.sync = retval
                self._set_local_height()
            except Exception, e:
                sys.stderr.write('Error! %s: %s\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()

    def is_running(self):
        with self.lock:
            return self.running

    def is_synced(self):
        with self.lock:
            return self.sync

    def stop(self):
        with self.lock:
            self.running = False
        self.newBlocks.stop()

    @property
    def height(self):
        return self.local_height

    def get_header(self, height):
        return self.store.read_header(height)

    def _set_local_height(self):
        h = self.store.get_height()
        if self.local_height != h:
            self.local_height = h

    def _reorg(self, height):
        sys.stderr.write('reorg blockchain from %d\n' % height)
        sys.stderr.flush()
        if hasattr(self.txdb, 'drop_from_height'):
            self.txdb.drop_from_height(height)
        self.txdb.store.drop_from_height(height)

    def _get_chunks(self, header):
        max_index = (header['block_height'] + 1)/2016
        index = min((self.height+1)/2016, max_index)
        reorg_from = None

        while self.is_running():
            if index > max_index:
                return True

            chunk = self.bcs.get_chunk(index)
            if not chunk:
                return False
            chunk = chunk.decode('hex')

            if index == 0:
                prev_hash = "0"*64
                if reorg_from is not None:
                    reorg_from = 0
            else:
                prev_header = self.store.read_raw_header(index*2016-1)
                if prev_header is None:
                    return False
                prev_hash = self.bha.hash_header(prev_header)
            chunk_first_header = self.store.header_from_raw(chunk[:80])
            if chunk_first_header['prev_block_hash'] != prev_hash:
                reorg_from = index*2016
                index -= 1
                continue

            if reorg_from is not None:
                self._reorg(reorg_from)
                reorg_from = None
            try:
                self.bha.verify_chunk(index, chunk)
            except Exception, e:
                sys.stderr.write('Verify chunk failed! (%s: %s)\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                return False

            self.store.truncate(index*2016)
            self.store.save_chunk(index, chunk)
            index += 1

    def _get_chain(self, header):
        chain = [header]
        requested_height = None
        reorg_from = None

        while self.is_running():
            if requested_height is not None:
                header = self.bcs.get_header(requested_height)
                if not header:
                    return False
                chain = [header] + chain
                requested_height = None
                continue

            prev_height = header.get('block_height') - 1
            prev_header = self.store.read_raw_header(prev_height)
            if prev_header is None:
                requested_height = prev_height
                continue

            prev_hash = self.bha.hash_header(prev_header)
            if prev_hash != header.get('prev_block_hash'):
                requested_height = prev_height
                reorg_from = prev_height
                continue

            if reorg_from is not None:
                self._reorg(reorg_from)
                reorg_from = None
            try:
                self.bha.verify_chain(chain)
            except Exception, e:
                sys.stderr.write('Verify chain failed! (%s: %s)\n' % (type(e), e))
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                return False

            self.store.truncate(chain[0]['block_height'])
            self.store.save_chain(chain)
            return True
