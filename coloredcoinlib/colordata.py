class ThickColorData(object):
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
            raise Exception("transaction isn't in blockchain yet")
