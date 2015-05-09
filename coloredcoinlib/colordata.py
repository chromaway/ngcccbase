""" Color data representation objects."""
import time


from colordef import ColorDefinition, UNCOLORED_MARKER
from colorvalue import SimpleColorValue


class UnfoundTransactionError(Exception):
    pass


class ColorData(object):
    """Base color data class"""
    pass


class StoredColorData(ColorData):

    def __init__(self, cdbuilder_manager, blockchain_state, cdstore, colormap):
        self.cdbuilder_manager = cdbuilder_manager
        self.blockchain_state = blockchain_state
        self.cdstore = cdstore
        self.colormap = colormap

    def _fetch_colorvalues(self, color_id_set, txhash, outindex,
                           cvclass=SimpleColorValue):
        """returns colorvalues currently present in cdstore"""

        adduncolored = False
        if 0 in color_id_set:
            color_id_set.remove(0)
            adduncolored = True

        ret = []
        for entry in self.cdstore.get_any(txhash, outindex):
            color_id, value, label = entry
            if color_id in color_id_set:
                color_def = self.colormap.get_color_def(color_id)
                ret.append(cvclass(colordef=color_def, value=value,
                                   label=label))

        if adduncolored:
            tx = self.blockchain_state.get_tx(txhash)
            value = tx.outputs[outindex].value
            ret.append(cvclass(colordef=UNCOLORED_MARKER, value=value))
            color_id_set.add(0)

        return ret

    def get_colorvalues_raw(self, color_id, ctx):
        """get colorvalues for all outputs of a raw transaction
        (which is, possibly, not in the blockchain yet)
        """
        color_id_set = set([color_id])
        color_def = self.cdbuilder_manager.colormap.get_color_def(color_id)
        in_colorvalues = []
        for inp in ctx.inputs:
            cvs = self.get_colorvalues(color_id_set,
                                       inp.prevout.hash,
                                       inp.prevout.n)
            cv = cvs[0] if cvs else None
            in_colorvalues.append(cv)
        return color_def.run_kernel(ctx, in_colorvalues)


class ThickColorData(StoredColorData):
    """ Color data which needs access to the whole blockchain state"""
    def __init__(self, *args, **kwargs):
        super(ThickColorData, self).__init__(*args, **kwargs)
        self.mempool_cache = []

    def get_colorvalues(self, color_id_set, txhash, outindex):
        blockhash, found = self.blockchain_state.get_tx_blockhash(txhash)
        if not found:
            raise UnfoundTransactionError("Transaction %s not found!" % txhash)
        if blockhash:
            self.cdbuilder_manager.ensure_scanned_upto(color_id_set, blockhash)
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
            if txhash not in [tx.hash for tx in mempool]:
                raise UnfoundTransactionError("Transaction %s not found in mempool!" % txhash)
            # the preceding blockchain
            self.cdbuilder_manager.ensure_scanned_upto(
                color_id_set, best_blockhash)
            # scan everything in the mempool
            for tx in mempool:
                self.cdbuilder_manager.scan_tx(color_id_set, tx)
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

        scanned_outputs = set()
        
        def maxdepthreached(txid):
            current_height = self.blockchain_state.get_tx_height(txid)
            for color_id, color_def in color_def_map.items():
                genesistxid = color_def.genesis["txhash"]
                genesisheight = self.blockchain_state.get_tx_height(genesistxid)
                if current_height > genesisheight:
                    return False
            return True

        def process(current_txhash, current_outindex):
            """For any tx out, process the colorvalues of the affecting
            inputs first and then scan that tx.
            """
            if (current_txhash, current_outindex) in scanned_outputs:
                return
            scanned_outputs.add((current_txhash, current_outindex))

            if self._fetch_colorvalues(color_id_set, current_txhash, current_outindex):
                return

            current_tx = self.blockchain_state.get_tx(current_txhash)

            # note a genesis tx will simply have 0 affecting inputs
            inputs = set()
            for color_id, color_def in color_def_map.items():
                if color_def == UNCOLORED_MARKER:
                    continue
                affecting_inputs = color_def.get_affecting_inputs(
                    current_tx, [current_outindex]
                )
                inputs = inputs.union(affecting_inputs)
            for i in inputs:
                # fixme stop recursion
                if not maxdepthreached(current_txhash):
                    process(i.prevout.hash, i.prevout.n)
            self.cdbuilder_manager.scan_tx(color_id_set, current_tx, [current_outindex])

        process(txhash, outindex)
        return self._fetch_colorvalues(color_id_set, txhash, outindex)

