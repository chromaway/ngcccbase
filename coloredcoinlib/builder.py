from logger import log

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
        in_colorstates = []
        empty = True
        for inp in tx.inputs:
            val = self.cdstore.get(self.color_id, inp.outpoint.hash, inp.outpoint.n)
            in_colorstates.append(val)
            if val:
                empty = False
        if empty and not (self.colordef.is_special_tx(tx)):
            return
        out_colorstates = self.colordef.run_kernel(tx, in_colorstates)
        for oi in xrange(len(out_colorstates)):
            val = out_colorstates[oi]
            if val:
                self.cdstore.add(self.color_id, tx.hash, oi, val[0], val[1])


class FullScanColorDataBuilder(BasicColorDataBuilder):
    """color data builder based on exhaustive blockchain scan, for one specific color"""
    def __init__(self, cdstore, blockchain_state, colordef, metastore):
        super(FullScanColorDataBuilder, self).__init__(cdstore, blockchain_state, colordef)
        self.metastore = metastore
        self.cur_height = metastore.get_scan_height(self.color_id)

    def scan_blockchain(self, from_height, to_height):
        for i in xrange(from_height, to_height + 1):
            self.scan_block(i)
            return

    def scan_block(self, height):
        log("scanning block at height %s" % height)
        for tx in self.blockchain_state.iter_block_txs(height):
            self.scan_tx(tx)
        self.metastore.set_scan_height(self.color_id, height)

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
