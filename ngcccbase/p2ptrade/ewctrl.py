from collections import defaultdict

from coloredcoinlib import (ColorSet, ColorTarget, UNCOLORED_MARKER,
                            InvalidColorIdError, ZeroSelectError,
                            OperationalTxSpec, SimpleColorValue)
from protocol_objects import ETxSpec
from ngcccbase.asset import AdditiveAssetValue
from ngcccbase.txcons import InsufficientFundsError
from ngcccbase.utxodb import UTXO


FEE = SimpleColorValue(colordef=UNCOLORED_MARKER, value=15000)

class OperationalETxSpec(OperationalTxSpec):
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
        for colordef, inps in etx_spec.inputs.items():
            if colordef == UNCOLORED_MARKER:
                for inp in inps:
                    tx = self.model.ccc.blockchain_state.get_tx(inp[0])
                    value = tx.outputs[inp[1]].value
                    self.inputs[0].append((value, inp))
            else:
                color_id_set = set([colordef.get_color_id()])
                for inp in inps:
                    
                    css = colordata.get_colorvalues(color_id_set, inp[0], inp[1])
                    if (css and len(css) == 1):
                        cs = css[0]
                        self.inputs[cs.get_color_id()].append((cs.get_value(),
                                                               inp))

    def prepare_targets(self, etx_spec, their):
        self.targets = etx_spec.targets
        wam = self.model.get_address_manager()
        colormap = self.model.get_color_map()
        their_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [their.get_color_id()]) 
        ct = ColorTarget(wam.get_change_address(their_color_set).get_address(),
                         their)
        self.targets.append(ct)

    def get_required_fee(self, tx_size):
        return FEE

    def select_coins(self, colorvalue):
        colordef = colorvalue.get_colordef()
        color_id = colordef.get_color_id()
        cq = self.model.make_coin_query({"color_id_set": set([color_id])})
        utxo_list = cq.get_result()

        zero = ssum = SimpleColorValue(colordef=colordef, value=0)
        selection = []
        if colorvalue == zero:
            raise ZeroSelectError('cannot select 0 coins')
        for utxo in utxo_list:
            ssum += SimpleColorValue.sum(utxo.colorvalues)
            selection.append(utxo)
            if ssum >= colorvalue:
                return selection, ssum
        raise InsufficientFundsError('not enough coins: %s requested, %s found'
                                     % (colorvalue, ssum))


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
            raise InvalidColorIdError("color spec not recognized")
        return ColorSet.from_color_ids(self.model.get_color_map(), [color_id])

    def select_inputs(self, colorvalue):
        cs = ColorSet.from_color_ids(self.model.get_color_map(),
                                     [colorvalue.get_color_id()])

        cq = self.model.make_coin_query({"color_set": cs})
        utxo_list = cq.get_result()
        selection = []
        csum = SimpleColorValue(colordef=colorvalue.get_colordef(), value=0)

        for utxo in utxo_list:
            csum += SimpleColorValue.sum(utxo.colorvalues)
            selection.append(utxo)
            if csum >= colorvalue:
                break
        if csum < colorvalue:
            raise InsufficientFundsError('not enough money')
        return selection, (csum - colorvalue)

    def make_etx_spec(self, our, their):
        fee = FEE if our.get_colordef() == UNCOLORED_MARKER else 0
        c_utxos, c_change = self.select_inputs(our + fee)
        inputs = {our.get_colordef(): 
                  [utxo.get_outpoint() for utxo in c_utxos]}
        wam = self.model.get_address_manager()
        our_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                [our.get_color_id()]) 
        their_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [their.get_color_id()]) 
        our_address = wam.get_change_address(their_color_set)
        targets = [ColorTarget(our_address.get_address(), their)]
        if c_change > 0:
            our_change_address = wam.get_change_address(our_color_set)
            targets.append(ColorTarget(our_change_address.get_address(),
                                       c_change))
        return ETxSpec(inputs, targets, c_utxos)

    def make_reply_tx(self, etx_spec, our, their):
        op_tx_spec = OperationalETxSpec(self.model, self)
        op_tx_spec.prepare_inputs(etx_spec)
        op_tx_spec.prepare_targets(etx_spec, their)
        signed_tx = self.model.transform_tx_spec(op_tx_spec, 'signed')
        return signed_tx
