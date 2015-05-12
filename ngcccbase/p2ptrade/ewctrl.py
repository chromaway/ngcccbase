from collections import defaultdict

from coloredcoinlib import (ColorSet, ColorTarget, UNCOLORED_MARKER,
                            InvalidColorIdError, ZeroSelectError,
                            SimpleColorValue, CTransaction)
from protocol_objects import ETxSpec
from ngcccbase.asset import AdditiveAssetValue
from ngcccbase.txcons import (BaseOperationalTxSpec,
                              SimpleOperationalTxSpec, InsufficientFundsError)
from ngcccbase.coindb import UTXO

import bitcoin.core
from bitcoin.wallet import CBitcoinAddress


class OperationalETxSpec(SimpleOperationalTxSpec):

    def __init__(self, model, ewctrl):
        self.model = model
        self.ewctrl = ewctrl
        self.our_value_limit = None

    def get_targets(self):
        return self.targets

    def get_change_addr(self, color_def):
        color_id = color_def.color_id
        cs = ColorSet.from_color_ids(self.model.get_color_map(), [color_id])
        wam = self.model.get_address_manager()
        return wam.get_change_address(cs).get_address()

    def set_our_value_limit(self, our):
        our_colordef = self.ewctrl.resolve_color_spec(our['color_spec'])
        self.our_value_limit = SimpleColorValue(colordef=our_colordef,
                                                value=our['value'])

    def prepare_inputs(self, etx_spec):
        self.inputs = defaultdict(list)
        colordata = self.model.ccc.colordata
        for color_spec, inps in etx_spec.inputs.items():
            colordef = self.ewctrl.resolve_color_spec(color_spec)
            color_id_set = set([colordef.get_color_id()])
            for inp in inps:
                txhash, outindex = inp
                tx = self.model.ccc.blockchain_state.get_tx(txhash)
                prevout = tx.outputs[outindex]
                utxo = UTXO({"txhash": txhash,
                             "outindex": outindex,
                             "value": prevout.value,
                             "script": prevout.script})
                colorvalue = None
                if colordef == UNCOLORED_MARKER:
                    colorvalue = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                                  value=prevout.value)
                else:
                    css = colordata.get_colorvalues(color_id_set,
                                                    txhash,
                                                    outindex)
                    if (css and len(css) == 1):
                        colorvalue = css[0]
                if colorvalue:
                    self.inputs[colordef.get_color_id()].append(
                        (colorvalue, utxo))

    def prepare_targets(self, etx_spec, their):
        self.targets = []
        for address, color_spec, value in etx_spec.targets:
            colordef = self.ewctrl.resolve_color_spec(color_spec)
            self.targets.append(ColorTarget(address,
                                       SimpleColorValue(colordef=colordef,
                                                        value=value)))
        wam = self.model.get_address_manager()
        colormap = self.model.get_color_map()
        their_colordef = self.ewctrl.resolve_color_spec(their['color_spec'])
        their_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [their_colordef.get_color_id()])
        ct = ColorTarget(wam.get_change_address(their_color_set).get_address(),
                         SimpleColorValue(colordef=their_colordef,
                                          value=their['value']))
        self.targets.append(ct)

    def select_uncolored_coins(self, colorvalue, use_fee_estimator):
        selected_inputs = []
        selected_value = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                          value=0)
        if use_fee_estimator:
            needed = colorvalue + use_fee_estimator.estimate_required_fee()
        else:
            needed = colorvalue
        color_id = 0
        if color_id in self.inputs:
            total = SimpleColorValue.sum([cv_u[0]
                                          for cv_u in self.inputs[color_id]])
            needed -= total
            selected_inputs += [cv_u[1]
                               for cv_u in self.inputs[color_id]]
            selected_value += total
        if needed > 0:
            value_limit = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=10000+8192*2)
            if self.our_value_limit.is_uncolored():
                value_limit += self.our_value_limit
            if needed > value_limit:
                msg = "Exceeded limits: %s requested, %s found!"
                raise InsufficientFundsError(msg % (needed, value_limit))
            our_inputs, our_value = super(OperationalETxSpec, self).\
                select_coins(colorvalue - selected_value, use_fee_estimator)
            selected_inputs += our_inputs
            selected_value += our_value
        return selected_inputs, selected_value

    def select_coins(self, colorvalue, use_fee_estimator=None):
        self._validate_select_coins_parameters(colorvalue, use_fee_estimator)
        colordef = colorvalue.get_colordef()
        if colordef == UNCOLORED_MARKER:
            return self.select_uncolored_coins(colorvalue, use_fee_estimator)

        color_id = colordef.get_color_id()
        if color_id in self.inputs:
            # use inputs provided in proposal
            total = SimpleColorValue.sum([cv_u[0]
                                          for cv_u in self.inputs[color_id]])
            if total < colorvalue:
                msg = 'Not enough coins: %s requested, %s found!'
                raise InsufficientFundsError(msg % (colorvalue, total))
            return [cv_u[1] for cv_u in self.inputs[color_id]], total

        if colorvalue > self.our_value_limit:
            raise InsufficientFundsError("%s requested, %s found!"
                                         % (colorvalue, self.our_value_limit))
        return super(OperationalETxSpec, self).select_coins(colorvalue)


class EWalletController(object):
    def __init__(self, model, wctrl):
        self.model = model
        self.wctrl = wctrl

    def publish_tx(self, raw_tx, my_offer):
        txhash = raw_tx.get_hex_txhash()
        self.model.tx_history.add_trade_entry(
            txhash,
            self.offer_side_to_colorvalue(my_offer.B),
            self.offer_side_to_colorvalue(my_offer.A))
        self.wctrl.publish_tx(raw_tx)


    def check_tx(self, raw_tx, etx_spec):
        """check if raw tx satisfies spec's targets"""
        bctx = bitcoin.core.CTransaction.deserialize(raw_tx.get_tx_data())
        ctx = CTransaction.from_bitcoincore(raw_tx.get_hex_txhash(),
                                            bctx,
                                            self.model.ccc.blockchain_state)
        color_id_set = set([])
        targets = []
        for target in etx_spec.targets:
            our_address, color_spec, value = target
            raw_addr = CBitcoinAddress(our_address)
            color_def = self.resolve_color_spec(color_spec)
            color_id = color_def.get_color_id()
            color_id_set.add(color_id)
            targets.append((raw_addr, color_id, value))

        used_outputs = set([])
        satisfied_targets = set([])

        for color_id in color_id_set:
            if color_id == 0:
                continue
            out_colorvalues = self.model.ccc.colordata.get_colorvalues_raw(
                color_id, ctx)
            for oi in range(len(ctx.outputs)):
                if oi in used_outputs:
                    continue
                if out_colorvalues[oi]:
                    for target in targets:
                        if target in satisfied_targets:
                            continue
                        raw_address, tgt_color_id, value = target
                        if ((tgt_color_id == color_id) and
                            (value == out_colorvalues[oi].get_value()) and
                            (raw_address == ctx.outputs[oi].raw_address)):
                                satisfied_targets.add(target)
                                used_outputs.add(oi)
        for target in targets:
            if target in satisfied_targets:
                continue
            raw_address, tgt_color_id, value = target
            if tgt_color_id == 0:
                for oi in range(len(ctx.outputs)):
                    if oi in used_outputs:
                        continue
                    if ((value == ctx.outputs[oi].value) and
                        (raw_address == ctx.outputs[oi].raw_address)):
                        satisfied_targets.add(target)
                        used_outputs.add(oi)
        return len(targets) == len(satisfied_targets)

    def resolve_color_spec(self, color_spec):
        colormap = self.model.get_color_map()
        return colormap.get_color_def(color_spec)

    def offer_side_to_colorvalue(self, side):
        colordef = self.resolve_color_spec(side['color_spec'])
        return SimpleColorValue(colordef=colordef,
                                value=side['value'])

    def select_inputs(self, colorvalue):
        op_tx_spec = SimpleOperationalTxSpec(self.model, None)
        if colorvalue.is_uncolored():
            composed_tx_spec = op_tx_spec.make_composed_tx_spec()
            selection, total = op_tx_spec.select_coins(colorvalue, composed_tx_spec)
            change = total - colorvalue - \
                composed_tx_spec.estimate_required_fee(extra_txins=len(selection))
            if change < op_tx_spec.get_dust_threshold():
                change = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                          value=0)
            return selection, change
        else:
            selection, total = op_tx_spec.select_coins(colorvalue)
            change = total - colorvalue
            return selection, change

    def make_etx_spec(self, our, their):
        our_color_def = self.resolve_color_spec(our['color_spec'])
        our_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [our_color_def.get_color_id()])
        their_color_def = self.resolve_color_spec(their['color_spec'])
        their_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [their_color_def.get_color_id()])
        extra_value = 0
        if our_color_def == UNCOLORED_MARKER:
            # pay fee + padding for one colored outputs
            extra_value = 10000 + 8192 * 1
        c_utxos, c_change = self.select_inputs(
            SimpleColorValue(colordef=our_color_def,
                             value=our['value'] + extra_value))
        inputs = {our['color_spec']:
                  [utxo.get_outpoint() for utxo in c_utxos]}
        wam = self.model.get_address_manager()

        our_address = wam.get_change_address(their_color_set)
        targets = [(our_address.get_address(),
                    their['color_spec'], their['value'])]
        if c_change > 0:
            our_change_address = wam.get_change_address(our_color_set)
            targets.append((our_change_address.get_address(),
                            our['color_spec'], c_change.get_value()))
        return ETxSpec(inputs, targets, c_utxos)

    def make_reply_tx(self, etx_spec, our, their):
        op_tx_spec = OperationalETxSpec(self.model, self)
        op_tx_spec.set_our_value_limit(our)
        op_tx_spec.prepare_inputs(etx_spec)
        op_tx_spec.prepare_targets(etx_spec, their)
        signed_tx = self.model.transform_tx_spec(op_tx_spec, 'signed')
        return signed_tx
