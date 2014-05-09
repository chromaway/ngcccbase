import time
from coloredcoinlib.store import PersistentDictStore
from asset import AdditiveAssetValue, AssetTarget

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


class TxHistory(object):
    def __init__(self, model):
        self.model = model
        self.entries = PersistentDictStore(
            self.model.store_conn.conn, "txhistory")
    
    def decode_entry(self, entry_data):
        print ('entry_data', entry_data)
        return TxHistoryEntry.from_data(self.model, entry_data)

    def get_entry(self, txhash):
        entry = self.entries.get(txhash)
        if entry:
            return self.decode_entry(entry)
        else:
            return None

    def add_send_entry(self, txhash, asset, target_addrs, target_values):
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'send',
                                "txtime": int(time.time()),
                                "asset_id": asset.get_id(),
                                "targets": zip(target_addrs, target_values)}

    def get_all_entries(self):
        return sorted([self.decode_entry(e) 
                       for e in self.entries.values()],
                      key=lambda txe: txe.txtime)

