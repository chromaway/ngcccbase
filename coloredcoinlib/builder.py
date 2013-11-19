""" Color data builder objects"""

from logger import log
from explorer import get_spends
from toposort import toposorted


class ColorDataBuilder(object):
    pass


class ColorDataBuilderManager(object):
    """Manages multiple color data builders, one per color"""
    def __init__(self, colormap, blockchain_state,
                 cdstore, metastore, builder_class):
        self.colormap = colormap
        self.metastore = metastore
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore
        self.builders = {}
        self.builder_class = builder_class

    def get_builder(self, color_id):
        if color_id in self.builders:
            return self.builders[color_id]
        colordef = self.colormap.get_color_def(color_id, self.blockchain_state)
        builder = self.builder_class(
            self.cdstore, self.blockchain_state, colordef, self.metastore)
        self.builders[color_id] = builder
        return builder

    def ensure_scanned_upto(self, color_id_set, blockhash):
        """ Ensure color data is available up to a given block"""
        for color_id in color_id_set:
            if color_id == 0:
                continue
            builder = self.get_builder(color_id)
            builder.ensure_scanned_upto(blockhash)


class BasicColorDataBuilder(ColorDataBuilder):
    """ Base class for color data builder algorithms"""
    def __init__(self, cdstore, blockchain_state, colordef):
        self.cdstore = cdstore
        self.blockchain_state = blockchain_state
        self.colordef = colordef
        self.color_id = colordef.color_id

    def scan_tx(self, tx):
        """ Scan transaction to obtain color data for its outputs. """
        in_colorvalues = []
        empty = True
        for inp in tx.inputs:
            val = self.cdstore.get(
                self.color_id, inp.outpoint.hash, inp.outpoint.n)
            in_colorvalues.append(val)
            if val:
                empty = False
        if empty and not (self.colordef.is_special_tx(tx)):
            return
        out_colorvalues = self.colordef.run_kernel(tx, in_colorvalues)
        for o_index, val in enumerate(out_colorvalues):
            if val:
                self.cdstore.add(
                    self.color_id, tx.hash, o_index, val[0], val[1])


class FullScanColorDataBuilder(BasicColorDataBuilder):
    """Color data builder based on exhaustive blockchain scan,
       for one specific color"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        super(FullScanColorDataBuilder, self).__init__(
            cdstore, blockchain_state, colordef)
        self.metastore = metastore

    def scan_block(self, blockhash):
        height = self.blockchain_state.get_block_height(blockhash)
        print "scanning block %s at %s" % (blockhash, height)
        for tx in self.blockchain_state.iter_block_txs(blockhash):
            self.scan_tx(tx)
        self.metastore.set_as_scanned(self.color_id, blockhash)

    def scan_blockchain(self, blocklist):
        for blockhash in blocklist:
            self.scan_block(blockhash)

    def ensure_scanned_upto(self, final_blockhash):
        if self.metastore.did_scan(self.color_id, final_blockhash):
            return
        min_height = self.colordef.genesis['height']

        # start from the final_blockhash and go backwards to build up
        #  the list of blocks to scan
        blockhash = final_blockhash
        blocklist = []
        while not self.metastore.did_scan(self.color_id, blockhash):
            blocklist.insert(0, blockhash)
            blockhash = self.blockchain_state.get_previous_blockhash(
                blockhash)
            height = self.blockchain_state.get_block_height(blockhash)
            if height < min_height:
                break

        self.scan_blockchain(blocklist)


class AidedColorDataBuilder(FullScanColorDataBuilder):
    """Color data builder based on following output spending transactions
        from the color's genesis transaction output, for one specific color"""

    def scan_blockchain(self, blocklist):
        txo_queue = [self.colordef.genesis]
        for blockhash in blocklist:
            # remove txs from this block from the queue
            block_txo_queue = [txo for txo in txo_queue
                               if txo['blockhash'] == blockhash]
            txo_queue = [txo for txo in txo_queue
                         if txo['blockhash'] != blockhash]

            block_txos = {}
            while block_txo_queue:
                txo = block_txo_queue.pop()
                if txo['txhash'] in block_txos:
                    # skip the ones we have already visited
                    continue
                block_txos[txo['txhash']] = txo
                spends = get_spends(txo['txhash'], self.blockchain_state)
                for stxo in spends:
                    if stxo['blockhash'] == blockhash:
                        block_txo_queue.append(stxo)
                    else:
                        txo_queue.append(stxo)

            block_txs = {}
            for txhash in block_txos.keys():
                block_txs[txhash] = self.blockchain_state.get_tx(txhash)

            def get_prev_txs(tx):
                """all transactions from current block this transaction
                   directly depends on"""
                prev_txs = []
                for inp in tx.inputs:
                    if inp.outpoint.hash in block_txs:
                        prev_txs.append(block_txs[inp.outpoint.hash])
                return prev_txs

            sorted_block_txs = toposorted(block_txs.values(), get_prev_txs)

            for tx in sorted_block_txs:
                self.scan_tx(tx)
            


if __name__ == "__main__":
    import blockchain
    import store
    import colormap as cm
    import colordata
    import datetime

    start = datetime.datetime.now()
    blockchain_state = blockchain.BlockchainState.from_url(None, True)

    store_conn = store.DataStoreConnection("test-color.db")
    cdstore = store.ColorDataStore(store_conn.conn)
    metastore = store.ColorMetaStore(store_conn.conn)

    colormap = cm.ColorMap(metastore)

    cdbuilder = ColorDataBuilderManager(
        colormap, blockchain_state, cdstore, metastore, AidedColorDataBuilder)
    colordata = colordata.ThickColorData(cdbuilder, blockchain_state, cdstore)
    blue_desc = "obc:" \
        "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e:" \
        "0:46442"
    red_desc = "obc:" \
        "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf:" \
        "0:46444"

    blue_id = colormap.resolve_color_desc(blue_desc)
    red_id = colormap.resolve_color_desc(red_desc)

    blue_set = set([blue_id])
    red_set = set([red_id])
    br_set = blue_set | red_set
    print br_set, ("Blue", "Red")

    g = colordata.get_colorvalues

    print g(
        br_set,
        "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e",
        0), "== 1000 Blue (blue genesis TX)"
    print g(
        br_set,
        "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf",
        0), "== 1000 Red (red genesis TX)"
    print g(
        br_set,
        "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e",
        1), "== None (blue genesis TX, other output)"
    print g(
        br_set,
        "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf",
        1), "== None (red genesis TX, other output)"
    print g(
        br_set,
        'c1d8d2fb75da30b7b61e109e70599c0187906e7610fe6b12c58eecc3062d1da5',
        0), "== Red"
    print g(
        br_set,
        '36af9510f65204ec5532ee62d3785584dc42a964013f4d40cfb8b94d27b30aa1',
        0), "== Red"
    print g(
        br_set,
        '3a60b70d425405f3e45f9ed93c30ca62b2a97e692f305836af38a524997dd01d',
        0), "== None (Random TX from blockchain)"
    print g(
        br_set,
        'c1d8d2fb75da30b7b61e109e70599c0187906e7610fe6b12c58eecc3062d1da5',
        0), "== Red"
    print g(
        br_set,
        '8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf',
        0), "== Red"
    print g(
        br_set,
        'f50f29906ce306be3fc06df74cc6a4ee151053c2621af8f449b9f62d86cf0647',
        0), "== Blue"
    print g(
        br_set,
        '7e40d2f414558be60481cbb976e78f2589bc6a9f04f38836c18ed3d10510dce5',
        0), "== Blue"
    print g(
        br_set,
        '4b60bb49734d6e26d798d685f76a409a5360aeddfddcb48102a7c7ec07243498',
        0), "== Red (Two-input merging TX)"
    print g(
        br_set,
        '342f119db7f9989f594d0f27e37bb5d652a3093f170de928b9ab7eed410f0bd1',
        0), "== None (Color mixing TX)"
    print g(
        br_set,
        'bd34141daf5138f62723009666b013e2682ac75a4264f088e75dbd6083fa2dba',
        0), "== Blue (complex chain TX)"
    print g(
        br_set,
        'bd34141daf5138f62723009666b013e2682ac75a4264f088e75dbd6083fa2dba',
        1), "== None (mining fee change output)"
    print g(
        br_set,
        '36af9510f65204ec5532ee62d3785584dc42a964013f4d40cfb8b94d27b30aa1',
        0), "== Red (complex chain TX)"
    print g(
        br_set,
        '741a53bf925510b67dc0d69f33eb2ad92e0a284a3172d4e82e2a145707935b3e',
        0), "== Red (complex chain TX)"
    print g(
        br_set,
        '741a53bf925510b67dc0d69f33eb2ad92e0a284a3172d4e82e2a145707935b3e',
        1), "== Red (complex chain TX)"
        
    print "Finished in", datetime.datetime.now() - start
