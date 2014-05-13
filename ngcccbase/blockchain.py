import os, sys, threading, Queue, time
import hashlib

from coloredcoinlib import BlockchainStateBase


class NewBlocks(threading.Thread):
    def __init__(self, bcs, queue):
        threading.Thread.__init__(self)
        self.running = False
        self.lock = threading.Lock()

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
                header = self.bcs.get_header(self.bcs.get_block_count())
                self.queue.put(header)
            except:
                pass
            run_time = time.time() + 30

    def is_running(self):
        with self.lock:
            return self.running

    def stop(self):
        with self.lock:
            self.running = False


class FileStore(object):
    def __init__(self, path):
        self.path = path

    def get_height(self):
        try:
            return os.path.getsize(self.path)/80 - 1
        except OSError, e:
            return 0

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

    def read_raw_header(self, height):
        try:
            with open(self.path, 'rb') as store:
                store.seek(height*80)
                data = store.read(80)
                assert len(data) == 80
                return data
        except (OSError, AssertionError), e:
            return None

    def read_header(self, height):
        data = self.read_raw_header(height)
        if data is not None:
            return self.header_from_raw(data)
        return None

    def save_chunk(self, index, chunk):
        with open(self.path, 'ab+') as store:
            store.seek(index*2016*80)
            store.write(chunk)

    def save_chain(self, chain):
        with open(self.path, 'ab+') as store:
            for header in chain:
                store.seek(header['height']*80)
                store.write(self.header_to_raw(header))


class BlockHashingAlgorithm(object):
    def __init__(self, store):
        self.store = store

    def hash_header(self, raw_header):
        import hashlib
        return hashlib.sha256(hashlib.sha256(raw_header).digest()).digest()[::-1].encode('hex_codec')

    def get_target(self, index, chain=None):
        if chain is None:
            chain = []

        max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        if index == 0: return 0x1d00ffff, max_target

        first = self.store.read_header((index-1)*2016)
        last = self.store.read_header(index*2016-1)
        if last is None:
            for h in chain:
                if h.get('height') == index*2016-1:
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
        new_target = min( max_target, (target * nActualTimespan)/nTargetTimespan )

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
            prev_header = self.store.read_raw_header(index*2016-1)
            if prev_header is None: raise
            prev_hash = self.hash_header(prev_header)

        bits, target = self.get_target(index)

        for i in range(num):
            raw_header = chunk[i*80:(i+1)*80]
            header = self.store.header_from_raw(raw_header)
            _hash = self.hash_header(raw_header)

            assert prev_hash == header.get('prev_block_hash')
            assert bits == header.get('bits')
            assert int('0x'+_hash, 16) < target

            prev_hash = _hash

    def verify_chain(self, chain):
        prev_hash = self.hash_header(
            self.store.read_raw_header(chain[0].get('height')-1))

        for header in chain:
            bits, target = self.get_target(header.get('height')/2016, chain)
            _hash = self.hash_header(self.store.header_to_raw(header))

            assert prev_hash == header.get('prev_block_hash')
            assert bits == header.get('bits')
            assert int('0x'+_hash, 16) < target

            prev_hash = _hash


class VerifierBlockchainState(BlockchainStateBase, threading.Thread):
    def __init__(self, path, bcs):
        threading.Thread.__init__(self)
        self.running = False
        self.lock = threading.Lock()
        self.queue = Queue.Queue()
        self.newBlocks = NewBlocks(bcs, self.queue)

        self.store = FileStore(os.path.join(path, 'blockchain_headers'))
        self.bha = BlockHashingAlgorithm(self.store)
        self.bcs = bcs

        self.local_height = 0
        self._set_local_height()

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

            print 'new header! (current height: %d, header height: %d)' % (self.height, header['height'])

            if header['height'] <= self.height:
                continue

            if header['height'] > self.height + 50:
                self._get_chunks(header['height'])
            else:
                self._get_chain(header)

    def is_running(self):
        with self.lock:
            return self.running

    def stop(self):
        with self.lock:
            self.running = False
        self.newBlocks.stop()

    @property
    def height(self):
        return self.local_height

    def _set_local_height(self):
        old = self.local_height
        h = self.store.get_height()
        if self.local_height != h:
            self.local_height = h
        if old != self.local_height:
            print 'new height! (%d --> %d)' % (old, self.local_height)

    def _get_chunks(self, height):
        min_index = (self.height + 1)/2016
        max_index = (height + 1)/2016
        for index in xrange(min_index, max_index+1):
            chunk = self.bcs.get_chunk(index)
            try:
                self.bha.verify_chunk(index, chunk)
            except Exception, e:
                sys.stderr.write('Verify chunk failed! (%s: %s)\n' % (type(e), e))
                sys.stderr.flush()
                return False
            self.store.save_chunk(index, chunk)
            self._set_local_height()
        return True

    def _get_chain(self, header):
        chain = [header]
        requested_hash = None

        while self.is_running():
            if requested_hash is not None:
                header = self.bcs.get_header(str(requested_hash))
                if not header:
                    return False
                chain = [header] + chain
                requested_hash = None
                continue

            height = header.get('height')
            prev_header = self.store.read_raw_header(height-1)
            if prev_header is None:
                requested_hash = header.get('prev_block_hash')
                continue

            prev_hash = self.bha.hash_header(prev_header)
            if prev_hash != header.get('prev_block_hash'):
                sys.stderr.write('reorg\n')
                sys.stderr.flush()
                requested_hash = header.get('prev_block_hash')
                continue

            try:
                self.bha.verify_chain(chain)
            except Exception, e:
                raise
                sys.stderr.write('Verify chain failed! (%s: %s)\n' % (type(e), e))
                sys.stderr.flush()
                return False

            self.store.save_chain(chain)
            self._set_local_height()
            return True
