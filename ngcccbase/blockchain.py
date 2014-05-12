import sys, threading, Queue, time

from coloredcoinlib import BlockchainStateBase
from coloredcoinlib.store import DataStore


class HeadersDataStore(DataStore):
    _SQL_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS headers_data (
    height INTEGER,
    version INTEGER,
    prev_block_hash VARCHAR(32),
    merkle_root VARCHAR(32),
    timestamp INTEGER,
    bits INTEGER,
    nonce INTEGER
);
    """

    _SQL_INDEX_HEIGHT = """\
CREATE UNIQUE INDEX IF NOT EXISTS headers_data_prev_block_hash ON headers_data (prev_block_hash);
    """

    _SQL_INDEX_PREV_BLOCK_HASH = """\
CREATE UNIQUE INDEX IF NOT EXISTS headers_data_prev_block_hash ON headers_data (prev_block_hash);
    """

    _SQL_INDEX_MERKLE_ROOT = """\
CREATE UNIQUE INDEX IF NOT EXISTS headers_data_merkle_root ON headers_data (merkle_root);
    """

    def __init__(self, conn):
        super(HeadersDataStore, self).__init__(conn)
        self.execute(self._SQL_CREATE_TABLE)
        self.execute(self._SQL_INDEX_HEIGHT)
        self.execute(self._SQL_INDEX_PREV_BLOCK_HASH)
        self.execute(self._SQL_INDEX_MERKLE_ROOT)

    def purge_headers(self):
        self.execute("DELETE FROM headers_data")

    def add_header(self, h):
        self.execute("INSERT INTO headers_data (version, prev_block_hash, merkle_root, timestamp, bits, nonce) VALUES (?, ?, ?, ?, ?, ?)",
            (h['version'], h['prev_block_hash'], h['merkle_root'], h['timestamp'], h['bits'], h['nonce']))

    def add_headers(self, headers):
        for header in headers:
            self.add_header(header)

    def get_header(self, height):
        return self.execute("SELECT * FROM headers_data WHERE height = ?",
            (height, )).fetchone()

    def get_header_by_prev_block_hash(self, prev_block_hash):
        return self.execute("SELECT * FROM headers_data WHERE prev_block_hash = ?",
            (prev_block_hash, )).fetchone()

    def get_header_by_merkle_root(self, merkle_root):
        return self.execute("SELECT * FROM headers_data WHERE merkle_root = ?",
            (merkle_root, )).fetchone()

    @property
    def height(self):
        return self.execute("SELECT height FROM headers_data ORDER BY height DESC LIMIT 1").fetchone() or 0


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
                block = self.bcs.get_block(self.bcs.get_block_count())
                self.queue.put({
                    'height':          block['height'],
                    'version':         block['version'],
                    'prev_block_hash': block['previousblockhash'],
                    'merkle_root':     block['merkleroot'],
                    'timestamp':       block['time'],
                    'bits':            block['bits'],
                    'nonce':           block['nonce'],
                })
            except:
                pass
            run_time = time.time() + 30

    def is_running(self):
        with self.lock:
            return self.running

    def stop(self):
        with self.lock:
            self.running = False


class VerifierBlockchainState(BlockchainStateBase, threading.Thread):
    def __init__(self, store_conn, bcs):
        threading.Thread.__init__(self)
        self.running = False
        self.lock = threading.Lock()
        self.queue = Queue.Queue()
        self.newBlocks = NewBlocks(bcs, self.queue)
        
        self.store = HeadersDataStore(store_conn.conn)
        self.bcs = bcs

        self.local_height = 0
        self._set_local_height()

    def run(self):
        with self.lock:
            self.running = True

        self.newBlocks.start()
        while self.is_running():
            try:
                block = self.queue.get_nowait()
            except Queue.Empty:
                time.sleep(0.05)
                continue

            if block['height'] <= self.height:
                continue

            if block['height'] > self.height + 50:
                self._get_verifiy_and_save_chunks(1)
                self.stop()
                #self._get_verifiy_and_save_chunks(block['height'])
                continue

            #chain = self.get_chain( i, header )
            #self.verify_chain( chain ):
            #self.save_header(header)

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
        h = self.store.height
        if h != self.local_height:
            self.local_height = h

    def _verify_chunk(self, index, chunk):
        height = index*2016
        num = len(chunk)/80

        if index == 0:  
            previous_hash = ("0"*64)
        else:
            raise
            #prev_header = self.read_header(index*2016-1)
            #if prev_header is None: raise
            #previous_hash = self.hash_header(prev_header)

        bits, target = self.get_target(index)

        print previous_hash


    def _save_chunk(self, chunk):
        pass

    def _get_verifiy_and_save_chunks(self, height):
        min_index = (self.height + 1)/2016
        max_index = (height + 1)/2016
        for index in xrange(min_index, max_index+1):
            try:
                chunk = self.bcs.get_chunk(index)
                self._verify_chunk(index, chunk)
            except Exception, e:
                sys.stderr.write('Verify chunk failed! (%s)\n' % e)
                sys.stderr.flush()
                return False
            self._save_chunk(chunk)
        return True
