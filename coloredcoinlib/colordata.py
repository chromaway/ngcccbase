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
        self.mempool_cache = []

    def _fetch_colorvalues(self, color_id_set, txhash, outindex):
        """returns colorvalues currently present in cdstore"""
        res = self.cdstore.get_any(txhash, outindex)
        return [entry for entry in res
                if entry[0] in color_id_set]

    def get_colorvalues(self, color_id_set, txhash, outindex):
        blockhash, found = self.blockchain_state.get_tx_blockhash(txhash)
        if not found:
            raise Exception("transaction %s isn't found" % txhash)
        if blockhash:
            self.cdbuilder_manager.ensure_scanned_upto(
                color_id_set, blockhash)
            return self._fetch_colorvalues(color_id_set, txhash, outindex)
        else:
            # not in the blockchain, but might be in the memory pool
            best_blockhash = None
            while 1:
                best_blockhash_prev = self.blockchain_state.get_best_blockhash()
                mempool = self.blockchain_state.get_mempool_txs()
                best_blockhash = self.blockchain_state.get_best_blockhash()
                if best_blockhash_prev == best_blockhash:
                    break
            if not (txhash in mempool):
                raise Exception("transaction %s isn't found in mempool" % txhash)
            # the preceding blockchain
            self.cdbuilder_manager.ensure_scanned_upto(
                color_id_set, best_blockhash)
            # scan everything in the mempool
            for h in mempool:
                self.cdbuilder_manager.scan_txhash(color_id_set, h)
            return self._fetch_colorvalues(color_id_set, txhash, outindex)
