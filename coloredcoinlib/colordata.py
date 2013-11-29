""" Color data representation objects."""
import time


class ColorData(object):
    """Base color data class"""
    pass


class StoredColorData(ColorData):

    def __init__(self, cdbuilder_manager, blockchain_state, cdstore):
        self.cdbuilder_manager = cdbuilder_manager
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore

    def _fetch_colorvalues(self, color_id_set, txhash, outindex):
        """returns colorvalues currently present in cdstore"""
        res = self.cdstore.get_any(txhash, outindex)
        return [entry for entry in res
                if entry[0] in color_id_set]


class ThickColorData(StoredColorData):
    """ Color data which needs access to the whole blockchain state"""
    def __init__(self, *args, **kwargs):
        super(ThickColorData, self).__init__(*args, **kwargs)
        self.mempool_cache = []

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

class ThinColorData(StoredColorData):
    """ Color data which needs access to the blockchain state up to the genesis of
        color."""
    def get_colorvalues(self, color_id_set, txhash, outindex):
        """
        for a given transaction <txhash> and output <outindex> and color
        <color_id_set>, return a list of dicts that looks like this:
        {
        'color_id': <color id>,
        'value': <colorvalue of this output>,
        'label': <currently unused>,
        }
        These correspond to the colorvalues of particular color ids for this
        output. Currently, each output should have a single element in the list.
        """
        color_def_map = self.cdbuilder_manager.get_color_def_map(color_id_set)

        tx_lookup = {}

        def process(current_txhash, current_outindex):
            """For any tx out, process the colorvalues of the affecting
            inputs first and then scan that tx.
            """
            if tx_lookup.get(current_txhash):
                return
            current_tx = self.blockchain_state.get_tx(current_txhash)
            tx_lookup[current_txhash] = current_tx
            if not current_tx:
                raise Exception("can't find transaction %s" % current_txhash)

            # note a genesis tx will simply have 0 affecting inputs
            inputs = set()
            for color_id, color_def in color_def_map.items():
                inputs = inputs.union(
                    color_def.get_affecting_inputs(current_tx,
                                                   [current_outindex]))
            for i in inputs:
                process(i.outpoint.hash, i.outpoint.n)
            self.cdbuilder_manager.scan_txhash(color_id_set, current_tx.hash)

        process(txhash, outindex)
        return self._fetch_colorvalues(color_id_set, txhash, outindex)
