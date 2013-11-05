from logger import log
from explorer import get_spends
from toposort import toposorted

class ColorDataBuilder(object):
    pass

class ColorDataBuilderManager(object):
    """manages multiple color data builders, one per color"""
    def __init__(self, colormap, blockchain_state, cdstore, metastore, builder_class):
        self.colormap = colormap
        self.metastore = metastore
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore
        self.builders = {}
        self.builder_class = builder_class
        
    def get_builder(self, color_id):
        if color_id in self.builders:
            return self.builders[color_id]
        colordef = self.colormap.get_color_def(color_id)
        builder = self.builder_class(self.cdstore,
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
            

class AidedColorDataBuilder(FullScanColorDataBuilder):
    """color data builder based on following output spending transactions, for one specific color"""

    def scan_blockchain(self, from_height, to_height):
        txo_queue = [self.colordef.genesis]
        for cur_block_height in xrange(self.colordef.starting_height, to_height+1):
            # remove txs from this block from the queue
            block_txo_queue = [txo for txo in txo_queue if txo['height'] == cur_block_height]
            txo_queue = [txo for txo in txo_queue if txo['height'] != cur_block_height]
            
            block_txos = {}
            while block_txo_queue:
                txo = block_txo_queue.pop()
                if txo['txhash'] in block_txos:
                    # skip the ones we have already visited
                    continue
                block_txos[txo['txhash']] = txo
                spends = get_spends(txo['txhash'], self.blockchain_state)
                for stxo in spends:
                    if stxo['height'] == cur_block_height:
                        block_txo_queue.append(stxo)
                    else:
                        txo_queue.append(stxo)

            block_txs = {}
            for txhash in block_txos.keys():
                block_txs[txhash] = self.blockchain_state.get_tx(txhash)

            def get_prev_txs(tx):
                """all transactions from current block this transaction directly depends on"""
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
    
    blockchain_state = blockchain.BlockchainState(None, True)

    store_conn = store.DataStoreConnection("test-color.db")
    cdstore = store.ColorDataStore(store_conn.conn)
    metastore = store.ColorMetaStore(store_conn.conn)

    colormap = cm.ColorMap(metastore)
    
    cdbuilder = ColorDataBuilderManager(colormap, blockchain_state,
                                cdstore, metastore,
                                AidedColorDataBuilder)
    colordata = colordata.ThickColorData(cdbuilder, blockchain_state, cdstore)
    color_desc = "obc:b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e:0:46442"

    color_id = colormap.resolve_color_desc(color_desc)
    print colordata.get_colorvalues(set([color_id]), 'c1d8d2fb75da30b7b61e109e70599c0187906e7610fe6b12c58eecc3062d1da5', 0)
    print colordata.get_colorvalues(set([color_id]), '36af9510f65204ec5532ee62d3785584dc42a964013f4d40cfb8b94d27b30aa1', 0)
    
    

    
