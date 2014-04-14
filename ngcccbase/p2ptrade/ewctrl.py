from collections import defaultdict

from coloredcoinlib import (ColorSet, ColorTarget, UNCOLORED_MARKER,
                            InvalidColorIdError, ZeroSelectError,
                            SimpleColorValue, CTransaction)
from protocol_objects import ETxSpec
from ngcccbase.asset import AdditiveAssetValue
from ngcccbase.txcons import BaseOperationalTxSpec, InsufficientFundsError
from ngcccbase.coindb import UTXO

import bitcoin.core
from bitcoin.wallet import CBitcoinAddress


class OperationalETxSpec(BaseOperationalTxSpec):
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

    def select_coins(self, colorvalue):
        colordef = colorvalue.get_colordef()
        color_id = colordef.get_color_id()

        if color_id in self.inputs:
            total = SimpleColorValue.sum([cv_u[0]
                                          for cv_u in self.inputs[color_id]])
            if total < colorvalue:
                raise InsufficientFundsError('not enough coins: %s requested, %s found'
                                             % (colorvalue, total))
            return [cv_u[1]
                    for cv_u in self.inputs[color_id]], total

        cq = self.model.make_coin_query({"color_id_set": set([color_id])})
        utxo_list = cq.get_result()

        zero = ssum = SimpleColorValue(colordef=colordef, value=0)
        selection = []
        if colorvalue == zero:
            raise ZeroSelectError('cannot select 0 coins')
        for utxo in utxo_list:
            if utxo.colorvalues:
                ssum += utxo.colorvalues[0]
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
            print out_colorvalues
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
        our_color_def = self.resolve_color_spec(our['color_spec'])
        our_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [our_color_def.get_color_id()])
        their_color_def = self.resolve_color_spec(their['color_spec'])
        their_color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                  [their_color_def.get_color_id()])
        extra_value = 0
        if our_color_def == UNCOLORED_MARKER:
            # pay fee + padding for two colored outputs
            extra_value = 10000 + 8192 * 2
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
        op_tx_spec.prepare_inputs(etx_spec)
        op_tx_spec.prepare_targets(etx_spec, their)
        signed_tx = self.model.transform_tx_spec(op_tx_spec, 'signed')
        return signed_tx
