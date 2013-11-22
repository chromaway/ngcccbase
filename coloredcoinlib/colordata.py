""" Color data representation objects."""
import time


class ColorData(object):
    """Base color data class"""
    pass


class ThickColorData(ColorData):
    """ Color data which needs access to the whole blockchain state"""
    def __init__(self, cdbuilder_manager, blockchain_state, cdstore):
        self.cdbuilder_manager = cdbuilder_manager
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore

    def get_colorvalues(self, color_id_set, txhash, outindex):
        blockhash = self.blockchain_state.get_tx_blockhash(txhash)
        if blockhash:
            self.cdbuilder_manager.ensure_scanned_upto(
                color_id_set, blockhash)
            res = self.cdstore.get_any(txhash, outindex)
            return [entry for entry in res
                    if entry[0] in color_id_set]
        else:
            # not in the blockchain, but might be in the memory pool
            mempool = self.blockchain_state.get_mempool_txs()

            wait = 1
            # wait until txhash is in the mempool
            while txhash not in mempool:
                print "waiting %s seconds for %s to show up in mempool" \
                    % (wait, txhash)
                mempool = self.blockchain_state.get_mempool_txs()
                time.sleep(1)
                wait += 1

            # scan everything in the mempool
            for h in mempool:
                self.cdbuilder_manager.scan_txhash(color_id_set, txhash)

            res = self.cdstore.get_any(txhash, outindex)
            return [entry for entry in res
                    if entry[0] in color_id_set]
