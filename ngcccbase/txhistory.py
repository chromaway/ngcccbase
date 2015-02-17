import time
from coloredcoinlib.store import PersistentDictStore
from asset import AdditiveAssetValue, AssetTarget
from txcons import RawTxSpec
from ngcccbase.address import AddressRecord

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
        if txtype == 'complex':
            return TxHistoryEntry_Complex(model, data)
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

    def get_fee_asset_target(self):
        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker("bitcoin")
        fee = self.model.get_blockchain_state().get_tx(self.txhash).get_fee()
        asset_value = AdditiveAssetValue(asset=asset, value=fee)
        return AssetTarget(None, asset_value)

    def get_targets(self):
        asset = self.get_asset()
        asset_targets = []
        for (tgt_addr, tgt_value) in self.targets:
            asset_value = AdditiveAssetValue(asset=asset, value=tgt_value)
            asset_targets.append(AssetTarget(tgt_addr, asset_value))
        asset_targets.append(self.get_fee_asset_target())
        return asset_targets

class TxHistoryEntry_Complex(TxHistoryEntry):
    def __init__(self, model, data):
        super(TxHistoryEntry_Complex, self).__init__(model, data)
        self.data = data

    def get_deltas(self):
        adm = self.model.get_asset_definition_manager()
        deltas = []
        for assetid, value in self.data['deltas'].items():
            deltas.append(adm.get_assetvalue_for_assetid_value(assetid, value))
        return deltas

    def get_addresses(self):
        return ", ".join(self.data['addresses'])

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
            asset_value = adm.get_assetvalue_for_colorvalue(
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

    def get_all_entries(self):
        return sorted([self.decode_entry(e)
                       for e in self.entries.values()],
                      key=lambda txe: txe.txtime)

    def populate_history(self):
        txdb = self.model.get_tx_db()
        for txhash in txdb.get_all_tx_hashes():
            if (txhash not in self.entries or            # new transaction
                    not self.entries[txhash]['txtime']): # update unconfirmed
                tx_data = txdb.get_tx_by_hash(txhash)['data']
                raw_tx  = RawTxSpec.from_tx_data(self.model,
                                                 tx_data.decode('hex'))
                self.add_entry_from_tx(raw_tx)

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

    def is_receive_entry(self, raw_tx, spent_coins, received_coins):
        return not spent_coins and received_coins

    def create_receive_entry(self, raw_tx, received_coins):
        txhash = raw_tx.get_hex_txhash()
        txtime = self.get_tx_timestamp(txhash)
        out_idxs = [coin.outindex for coin in received_coins]
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'receive',
                                "txtime": txtime,
                                "out_idxs": out_idxs}

    def add_trade_entry(self, txhash, in_colorvalue, out_colorvalue):
        adm = self.model.get_asset_definition_manager()
        in_assetvalue = adm.get_assetvalue_for_colorvalue(in_colorvalue)
        out_assetvalue = adm.get_assetvalue_for_colorvalue(out_colorvalue)
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

    def get_delta_color_values(self, spent_coins, received_coins):
        adm = self.model.get_asset_definition_manager()
        deltas = {}
        for coin in received_coins: # add received
            for cv in coin.get_colorvalues():
                colorid = cv.get_colordef().get_color_id()
                assetid = adm.get_asset_by_color_id(colorid).get_id()
                deltas[assetid] = deltas.get(assetid, 0) + cv.get_value()
        for coin in spent_coins: # subtract sent
            for cv in coin.get_colorvalues():
                colorid = cv.get_colordef().get_color_id()
                assetid = adm.get_asset_by_color_id(colorid).get_id()
                deltas[assetid] = deltas.get(assetid, 0) - cv.get_value()
        return dict(deltas)

    def create_complex_entry(self, raw_tx, spent_coins, received_coins):
        am = self.model.get_address_manager()
        txhash = raw_tx.get_hex_txhash()
        txtime = self.get_tx_timestamp(txhash)

        # get addresses
        outputs = raw_tx.composed_tx_spec.txouts
        wallet_addrs = set([r.address for r in am.get_all_addresses()])
        output_addrs = set([out.target_addr for out in outputs])
        send_addrs = list(output_addrs.difference(wallet_addrs))

        deltas = self.get_delta_color_values(spent_coins, received_coins)
        self.entries[txhash] = {
            "txhash": txhash,
            "txtype": 'complex',
            "txtime": txtime,
            "addresses" : send_addrs,
            "deltas" : deltas,
        }

    def is_send_entry(self, raw_tx, spent_coins, received_coins):
        am = self.model.get_address_manager()

        # only inputs from this wallet
        input_addrs = set(raw_tx.get_input_addresses())
        wallet_addrs = set([r.address for r in am.get_all_addresses()])
        if wallet_addrs.intersection(input_addrs) != input_addrs:
            return False # foreign inputs

        # only one color + uncolored sent
        cvlists = [coin.get_colorvalues() for coin in spent_coins]
        cvs = [item for sublist in cvlists for item in sublist] # flatten
        cids = set([cv.get_color_id() for cv in cvs])
        if len(cids) > 2 or (len(cids) == 2 and 0 not in cids):
            return False

        return False  # FIXME disabled for now

    def create_send_entry(self, raw_tx, spent_coins, received_coins):
        pass # TODO

    def add_send_entry(self, txhash, asset, target_addrs, target_values):
        self.entries[txhash] = {"txhash": txhash,
                                "txtype": 'send',
                                "txtime": int(time.time()),
                                "asset_id": asset.get_id(),
                                "targets": zip(target_addrs, target_values)}

    def add_entry_from_tx(self, raw_tx):
        coindb = self.model.get_coin_manager()
        spent_coins, received_coins = coindb.get_coins_for_transaction(raw_tx)
        if (not spent_coins) and (not received_coins):
            return # no effect

        # receive coins
        if self.is_receive_entry(raw_tx, spent_coins, received_coins):
            self.create_receive_entry(raw_tx, received_coins)

        # send coins
        elif self.is_send_entry(raw_tx, spent_coins, received_coins):
            self.create_send_entry(raw_tx, spent_coins, received_coins)

        else: # default for non obvious
            self.create_complex_entry(raw_tx, spent_coins, received_coins)



