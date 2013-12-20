from coloredcoinlib import txspec, ColorSet
from collections import defaultdict
from protocol_objects import ETxSpec
from ngcccbase.utxodb import UTXO


FEE = 15000

class OperationalETxSpec(txspec.OperationalTxSpec):
    def __init__(self, model, ewctrl):
        self.model = model
        self.ewctrl = ewctrl

    def get_targets(self):
        return self.targets

    def get_change_addr(self, color_def):
        color_id = color_def.color_id
        cs = ColorSet.from_color_ids(self.model.get_color_map(), [color_id])
        wam = self.model.get_address_manager()
        return wam.get_change_address(cs).get_address()

    def prepare_inputs(self, etx_spec):
        self.inputs = defaultdict(list)
        colordata = self.model.ccc.colordata
        for cspec, inps in etx_spec.inputs.items():
            color_set = self.ewctrl.resolve_color_spec(cspec)
            if color_set.uncolored_only():
                for inp in inps:
                    tx = self.model.ccc.blockchain_state.get_tx(inp[0])
                    value = tx.outputs[inp[1]].value
                    self.inputs[0].append((value, inp))
            else:
                for inp in inps:
                    css = colordata.get_colorvalues(color_set.color_id_set, inp[0], inp[1])
                    if (css and len(css) == 1):
                        cs = css[0]
                        self.inputs[cs[0]].append((cs[1], inp))

    def prepare_targets(self, etx_spec, their):
        self.targets = []
        colormap = self.model.get_color_map()
        for tgt_spec in etx_spec.targets:
            tgt_color_id = list(self.ewctrl.resolve_color_spec(tgt_spec[1]).color_id_set)[0]
            tgt_color_def = colormap.get_color_def(tgt_color_id)
            self.targets.append((tgt_spec[0], tgt_color_def, tgt_spec[2]))
        their_color_set = self.ewctrl.resolve_color_spec(their['color_spec'])
        wam = self.model.get_address_manager()
        their_color_id =  list(their_color_set.color_id_set)[0]
        their_color_def = colormap.get_color_def(their_color_id)
        self.targets.append(
            (wam.get_change_address(their_color_set).get_address(), their_color_def,
             their['value']))

    def get_required_fee(self, tx_size):
        return FEE

    def select_coins(self, color_def, value):
        color_id = color_def.color_id
        if color_id in self.inputs:
            c_inputs = self.inputs[color_id]
            tv = sum([inp[0] for inp in c_inputs])
            if tv < value:
                raise Exception('not enough coins')
            return [UTXO(inp[1][0], inp[1][1], inp[0], None)
                    for inp in c_inputs], tv
        else:
            color_id_set = set([color_id])
            cq = self.model.make_coin_query({"color_id_set": color_id_set})
            utxo_list = cq.get_result()

            ssum = 0
            selection = []
            if value == 0:
                raise Exception('cannot select 0 coins')
            for utxo in utxo_list:
                # TODO: use colorvalue!
                ssum += utxo.value
                selection.append(utxo)
                if ssum >= value:
                    return selection, ssum
            raise Exception('not enough coins to reach the target')


class EWalletController(object):
    def __init__(self, model, wctrl):
        self.model = model
        self.wctrl = wctrl

    def publish_tx(self, raw_tx):
        self.wctrl.publish_tx(raw_tx)

    def resolve_color_spec(self, color_spec):
        colormap = self.model.get_color_map()
        color_id = colormap.resolve_color_desc(color_spec, False)
        if color_id is None:
            raise Exception("color spec not recognized")
        return ColorSet.from_color_ids(self.model.get_color_map(), [color_id])

    def select_inputs(self, color_set, t_value):
        cq = self.model.make_coin_query({"color_set": color_set})
        utxo_list = cq.get_result()
        selection = []
        csum = 0
        for utxo in utxo_list:
            csum += utxo.value
            selection.append(utxo)
            if csum >= t_value:
                break
        if csum < t_value:
            raise Exception('not enough money')
        return selection, (csum - t_value)

    def make_etx_spec(self, our, their):
        our_color_set = self.resolve_color_spec(our['color_spec'])
        their_color_set = self.resolve_color_spec(their['color_spec'])
        fee = FEE if our_color_set.uncolored_only() else 0
        c_utxos, c_change = self.select_inputs(our_color_set,
                                               our['value'] + fee)
        inputs = {our['color_spec']: 
                  [utxo.get_outpoint() for utxo in c_utxos]}
        wam = self.model.get_address_manager()
        our_address = wam.get_change_address(their_color_set)
        targets = [(our_address.get_address(),
                    their['color_spec'], their['value'])]
        if c_change > 0:
            our_change_address = wam.get_change_address(our_color_set)
            targets.append((our_change_address.get_address(),
                            our['color_spec'], c_change))
        return ETxSpec(inputs, targets, c_utxos)

    def make_reply_tx(self, etx_spec, our, their):
        op_tx_spec = OperationalETxSpec(self.model, self)
        op_tx_spec.prepare_inputs(etx_spec)
        op_tx_spec.prepare_targets(etx_spec, their)
        signed_tx = self.model.transform_tx_spec(op_tx_spec, 'signed')
        return signed_tx
