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

    def get_color_def_map(self, color_id_set):
        """given a set of color_ids <color_id_set>, return
        a dict of color_id to color_def.
        """
        color_def_map = {}
        for color_id in color_id_set:
            color_def_map[color_id] = self.colormap.get_color_def(color_id)
        return color_def_map

    def get_builder(self, color_id):
        if color_id in self.builders:
            return self.builders[color_id]
        colordef = self.colormap.get_color_def(color_id)
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

    def scan_txhash(self, color_id_set, txhash):
        tx = self.blockchain_state.get_tx(txhash)
        self.scan_tx(color_id_set, tx)

    def scan_tx(self, color_id_set, tx):
        for color_id in color_id_set:
            if color_id == 0:
                continue
            builder = self.get_builder(color_id)
            builder.scan_tx(tx)


class BasicColorDataBuilder(ColorDataBuilder):
    """ Base class for color data builder algorithms"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        self.cdstore = cdstore
        self.blockchain_state = blockchain_state
        self.colordef = colordef
        self.color_id = colordef.color_id
        self.metastore = metastore

    def scan_tx(self, tx):
        """ Scan transaction to obtain color data for its outputs. """
        in_colorvalues = []
        empty = True
        for inp in tx.inputs:
            val = self.cdstore.get(
                self.color_id, inp.prevout.hash, inp.prevout.n)
            in_colorvalues.append(val)
            if val:
                empty = False
        if empty and not self.colordef.is_special_tx(tx):
            return
        out_colorvalues = self.colordef.run_kernel(tx, in_colorvalues)
        for o_index, val in enumerate(out_colorvalues):
            if val:
                self.cdstore.add(
                    self.color_id, tx.hash, o_index, val.get_value(), val.get_label())


class FullScanColorDataBuilder(BasicColorDataBuilder):
    """Color data builder based on exhaustive blockchain scan,
       for one specific color"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        super(FullScanColorDataBuilder, self).__init__(
            cdstore, blockchain_state, colordef, metastore)
        self.genesis_blockhash = self.blockchain_state.get_blockhash_at_height(
            self.colordef.genesis['height'])

    def scan_block(self, blockhash):
        if self.metastore.did_scan(self.color_id, blockhash):
            return
        log("scan block %s", blockhash)
        for tx in self.blockchain_state.iter_block_txs(blockhash):
            self.scan_tx(tx)
        self.metastore.set_as_scanned(self.color_id, blockhash)

    def scan_blockchain(self, blocklist):
        with self.cdstore.transaction():
            for i, blockhash in enumerate(blocklist):
                self.scan_block(blockhash)
                if i % 25 == 0:  # sync each 25 blocks
                    self.cdstore.sync()

    def ensure_scanned_upto(self, final_blockhash):
        if self.metastore.did_scan(self.color_id, final_blockhash):
            return

        # start from the final_blockhash and go backwards to build up
        #  the list of blocks to scan
        blockhash = final_blockhash
        genesis_height = self.blockchain_state.get_block_height(
            self.genesis_blockhash)
        blocklist = []
        while not self.metastore.did_scan(self.color_id, blockhash):
            log("recon block %s", blockhash)
            blocklist.insert(0, blockhash)
            blockhash, height = self.blockchain_state.get_previous_blockinfo(
                blockhash)
            if blockhash == self.genesis_blockhash:
                break  # pragma: no cover
            # sanity check
            if height < genesis_height:
                break  # pragma: no cover

        self.scan_blockchain(blocklist)


class AidedColorDataBuilder(FullScanColorDataBuilder):
    """Color data builder based on following output spending transactions
        from the color's genesis transaction output, for one specific color"""

    def scan_blockchain(self, blocklist):
        txo = self.colordef.genesis.copy()
        txo["blockhash"] = self.genesis_blockhash
        txo_queue = [txo]
        for blockhash in blocklist:
            if self.metastore.did_scan(self.color_id, blockhash):
                continue
            # remove txs from this block from the queue
            block_txo_queue = [txo for txo in txo_queue
                               if txo.get('blockhash') == blockhash]
            txo_queue = [txo for txo in txo_queue
                         if txo.get('blockhash') != blockhash]

            block_txos = {}
            while block_txo_queue:
                txo = block_txo_queue.pop()
                if txo['txhash'] in block_txos:
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
                    if inp.prevout.hash in block_txs:
                        prev_txs.append(block_txs[inp.prevout.hash])
                return prev_txs

            sorted_block_txs = toposorted(block_txs.values(), get_prev_txs)

            for tx in sorted_block_txs:
                self.scan_tx(tx)
            self.metastore.set_as_scanned(self.color_id, blockhash)
