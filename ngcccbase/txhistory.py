import time
from coloredcoinlib.store import PersistentDictStore
from asset import AdditiveAssetValue, AssetTarget
from txcons import RawTxSpec

def asset_value_to_data(av):
    return (av.get_asset().get_id(),
            av.get_value())

class TxHistoryEntry(object):
    def __init__(self, model, data):
        self.txhash = data['txhash']
        self.txtime = data['txtime']
        self.txtype = data['txtype']
        self.data = data
        self.model = model

    @classmethod
    def from_data(cls, model, data):
        txtype = data['txtype']
        if txtype == 'send':
            return TxHistoryEntry_Send(model, data)
        elif txtype == 'receive':
            return TxHistoryEntry_Receive(model, data)
        elif txtype == 'trade':
            return TxHistoryEntry_Trade(model, data)
        else:
            return TxHistoryEntry(model, data)


class TxHistoryEntry_Send(TxHistoryEntry):
    def __init__(self, model, data):
        super(TxHistoryEntry_Send, self).__init__(model, data)
        self.asset_id = data['asset_id']
        self.targets = data['targets']

    def get_asset(self):
        adm = self.model.get_asset_definition_manager()
        return adm.get_asset_by_id(self.asset_id)

    def get_targets(self):
        asset = self.get_asset()
        asset_targets = []
        for (tgt_addr, tgt_value) in self.targets:
            asset_value = AdditiveAssetValue(asset=asset,
                                             value=tgt_value)
            asset_targets.append(AssetTarget(tgt_addr, 
                                             asset_value))
        return asset_targets

class TxHistoryEntry_Receive(TxHistoryEntry):
    def __init__(self, model, data):
        super(TxHistoryEntry_Receive, self).__init__(model, data)
        self.out_idxs = data['out_idxs']
        
    def get_targets(self):
        targets = []
        coindb = self.model.get_coin_manager()
        adm = self.model.get_asset_definition_manager()
        for out_idx in self.out_idxs:
            coin = coindb.find_coin(self.txhash, out_idx)
            colorvalues = coin.get_colorvalues()
            if not colorvalues:
                continue
            assert len(colorvalues) == 1
            asset_value = adm.get_asset_value_for_colorvalue(
                colorvalues[0])
            targets.append(AssetTarget(coin.address,
                                       asset_value))
        return targets

class TxHistoryEntry_Trade(TxHistoryEntry):
    def __init__(self, model, data):
        TxHistoryEntry.__init__(self, model, data)
        self.in_values = data['in_values']
        self.out_values = data['out_values']
        
    def get_values(self, values):
        adm = self.model.get_asset_definition_manager()
        avalues = []
        for asset_id, value in values:
            asset = adm.get_asset_by_id(asset_id)
            avalues.append(AdditiveAssetValue(asset=asset,
                                             value=value))
        return avalues

    def get_in_values(self):
        return self.get_values(self.in_values)

    def get_out_values(self):
        return self.get_values(self.out_values)

    
class TxHistory(object):
    def __init__(self, model):
        self.model = model
        self.entries = PersistentDictStore(
            self.model.store_conn.conn, "txhistory")
    
    def decode_entry(self, entry_data):
        return TxHistoryEntry.from_data(self.model, entry_data)

    def get_entry(self, txhash):
        entry = self.entries.get(txhash)
        if entry:
            return self.decode_entry(entry)
        else:
            return None

    def add_send_entry(self, txhash, asset, target_addrs, target_values):
        txtime = self.get_tx_timestamp(txhash)
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'send',
                                "txtime": txtime,
                                "asset_id": asset.get_id(),
                                "targets": zip(target_addrs, target_values)}

    def get_all_entries(self):
        return sorted([self.decode_entry(e) 
                       for e in self.entries.values()],
                      key=lambda txe: txe.txtime)

    def _populate_history(self):
        txdb = self.model.get_tx_db()
        for txhash in txdb.get_all_tx_hashes():
            if txhash not in self.entries:
                tx_data = txdb.get_tx_by_hash(txhash)['data']
                raw_tx  = RawTxSpec.from_tx_data(self.model,
                                                 tx_data.decode('hex'))
                self.add_entry_from_tx(raw_tx)

    def populate_history(self):
        task = self._populate_history
        class AsyncTask(threading.Thread):
            def run(self):
                task()
        thread = AsyncTask()
        thread.start()

    def get_tx_timestamp(self, txhash): # TODO move to suitable file
        txtime = 0
        bs = self.model.get_blockchain_state()
        blockhash, x = bs.get_tx_blockhash(txhash)
        if blockhash:
            height = bs.get_block_height(blockhash)
            if height:
                header = bs.get_header(height)
                txtime = header.get('timestamp', txtime)
        return txtime

    def add_receive_entry(self, txhash, received_coins):
        txtime = self.get_tx_timestamp(txhash)
        out_idxs = [coin.outindex for coin in received_coins]
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'receive',
                                "txtime": txtime,
                                "out_idxs": out_idxs}

    def add_trade_entry(self, txhash, in_colorvalue, out_colorvalue):
        adm = self.model.get_asset_definition_manager()
        in_assetvalue = adm.get_asset_value_for_colorvalue(in_colorvalue)
        out_assetvalue = adm.get_asset_value_for_colorvalue(out_colorvalue)
        txtime = self.get_tx_timestamp(txhash)
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'trade',
                                "txtime": txtime,
                                "in_values": [asset_value_to_data(in_assetvalue)],
                                "out_values": [asset_value_to_data(out_assetvalue)]}
    
    def add_unknown_entry(self, txhash):
        txtime = self.get_tx_timestamp(txhash)
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'unknown',
                                "txtime": txtime}        
        
    
    def add_entry_from_tx(self, raw_tx):
        coindb = self.model.get_coin_manager()
        adm = self.model.get_asset_definition_manager()
        spent_coins, received_coins = coindb.get_coins_for_transaction(raw_tx)
        if (not spent_coins) and (not received_coins):
            return
        txhash = raw_tx.get_hex_txhash()
        if not spent_coins: # check for not spent because of change
            self.add_receive_entry(txhash, received_coins)
        else:
            # XXX assumes single color tx
            main_color_value = spent_coins[0].get_colorvalues()[0]
            asset = adm.get_asset_value_for_colorvalue(main_color_value).asset
            target_addrs = []
            target_values = []
            for coin in spent_coins: # FIXME use output address and value
                target_addrs.append(coin.address)
                target_values.append(coin.get_colorvalues()[0].get_value())
            self.add_send_entry(txhash, asset, target_addrs, target_values)



