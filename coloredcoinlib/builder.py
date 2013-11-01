from logger import log
from Queue import Queue
class ColorDataBuilder(object):
    pass

class ColorDataBuilderManager(object):
    """manages multiple color data builders, one per color"""
    def __init__(self, colormap, blockchain_state, cdstore, metastore):
        self.colormap = colormap
        self.metastore = metastore
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore
        self.builders = {}
    def get_builder(self, color_id):
        if color_id in self.builders:
            return self.builders[color_id]
        colordef = self.colormap.get_color_def(color_id)
        builder = FullScanColorDataBuilder(self.cdstore,
                                           self.blockchain_state,
                                           colordef,
                                           self.metastore)
        self.builders[color_id] = builder
        return builder
    def ensure_scanned_upto(self, color_id_set, block_height):
        for color_id in color_id_set:
            if color_id == 0:
                continue
            builder = self.get_builder(color_id)
            builder.ensure_scanned_upto(block_height)


class BasicColorDataBuilder(ColorDataBuilder):
    def __init__(self, cdstore, blockchain_state, colordef):
        self.cdstore = cdstore
        self.blockchain_state = blockchain_state
        self.colordef = colordef
        self.color_id = colordef.color_id

    def scan_tx(self, tx):
        in_colorvalues = []
        empty = True
        for inp in tx.inputs:
            val = self.cdstore.get(self.color_id, inp.outpoint.hash, inp.outpoint.n)
            in_colorvalues.append(val)
            if val:
                empty = False
        if empty and not (self.colordef.is_special_tx(tx)):
            return
        out_colorvalues = self.colordef.run_kernel(tx, in_colorvalues)
        for o_index, val in enumerate(out_colorvalues):
            if val:
                self.cdstore.add(self.color_id, tx.hash, o_index, val[0], val[1])


class FullScanColorDataBuilder(BasicColorDataBuilder):
    """color data builder based on exhaustive blockchain scan, for one specific color"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        super(FullScanColorDataBuilder, self).__init__(cdstore, blockchain_state, colordef)
        self.metastore = metastore
        self.cur_height = metastore.get_scan_height(self.color_id)

    def scan_blockchain(self, from_height, to_height):
        for i in xrange(from_height, to_height + 1):
            self.scan_block(i)

    def scan_block(self, height):
        log("scanning block at height %s" % height)
        for tx in self.blockchain_state.iter_block_txs(height):
            self.scan_tx(tx)
        self.cur_height = height
        self.metastore.set_scan_height(self.color_id, self.cur_height)

    def ensure_scanned_upto(self, block_height):
        if self.cur_height >= block_height:
            pass # up-to-date
        else:
            if self.cur_height:
                from_height = self.cur_height + 1
            else:
                # we cannot get genesis block via RPC, so we start from block 1
                from_height = self.colordef.starting_height or 1
            self.scan_blockchain(from_height, block_height)
            

class SetQueue(Queue):
    def _init(self, maxsize):
        self.queue = set()
    def _put(self, item):
        self.queue.add(item)
    def _get(self):
        return self.queue.pop()

class AidedColorDataBuilder(FullScanColorDataBuilder):
    """color data builder based on following output spending transactions, for one specific color"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        super(AidedColorDataBuilder, self).__init__(cdstore, blockchain_state, colordef, metastore)
        if not self.cur_height:
            self.scan_tx(colordef.genesis)
            self.cur_height = self.colordef.starting_height or 1

    def get_spends(self, tx):
        # TODO, using http://explorer.tumak.cz/spends
        return []

    def ensure_scanned_upto(self, block_height):
        if self.cur_height >= block_height:
            pass # up-to-date
        else:
            self.scan_color_history_to(self.cur_height, block_height)

    """ get transactions from a block height which contain colored outputs"""
    def get_txs_containing_color(self, height):
        def has_color_output(tx):
            for n, output in enumerate(tx.outputs):
                if self.cdstore.get(self.color_id, tx.hash, n):
                    return True
            return False
        return [tx for tx in self.blockchain_state.iter_block_txs(height)
                 if has_color_output(tx)]
            

    """ scans color's history from an already known block"""
    def scan_color_history(self, from_height, to_height):
        from_txs = self.get_txs_containing_color(from_height)
        tx_queue = SetQueue()
        for tx in from_txs:
            tx_queue.put(tx)
            
        while not tx_queue.empty():
            tx = tx_queue.get()
            if tx.block_height > to_height: # too far above
                continue
             
            spends = self.get_spends(tx)
            for stx in spends:
                tx_queue.put(stx)
            
            if tx in from_txs: # already scanned
                continue
            self.scan_tx(tx)


