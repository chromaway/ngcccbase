from logger import log

class ColorDataBuilder(object):
    pass

class CompositeColorDataBuilder(ColorDataBuilder):
    """manages multiple color data builders, one per color"""
    def __init__(self):
        self.builders = []
    def update(self):
        for b in self.builders:
            b.update()

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

    def update(self):
        if self.cur_height == self.blockchain_state.get_height():
            pass # up-to-date
        else:
            if self.cur_height:
                from_height = self.cur_height + 1
            else:
                # we cannot get genesis block via RPC, so we start from block 1
                from_height = self.colordef.starting_height or 1
            self.scan_blockchain(from_height, self.blockchain_state.get_height())
                
