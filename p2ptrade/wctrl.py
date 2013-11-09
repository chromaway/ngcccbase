from coloredcoinlib import txspec


class OperationalETxSpec(txspec.OperationalTxSpec):
    def __init__(self, model, ewctrl):
        self.model = model
        self.ewctrl = ewctrl

    def prepare_inputs(self, etx_spec, their):
        colordata = self.model.ccc.colordata
        for cspec, inps in etx_spec.inputs.items():
            color_set = self.ewctrl.resolve_color_spec(cspec)
            for inp in inps:
                cs = colordata.get_colorstates(color_set, inp[0], inp[1])
                
        

    def prepare_targets(self, etx_spec, their):
        self.targets = []
        for tgt_spec in etx_spec.targets:
            tgt_color_id = list(self.ewctrl.resolve_color_spec(tgt_spec[1]))[0]
            self.targets.append((tgt_spec[0], tgt_color_id, tgt_spec[2]))
        their_color_set = self.ewctrl.resolve_color_spec(their['color_spec'])
        wam = self.model.get_wallet_address_manager()
        self.targets.add((wam.get_change_address(their_color_set), list(their_color_set)[0],
                          their['value']))

        
        
        


    
    def select_coins(self, color_id, value):
        
        

class EWalletController(object):
    def __init__(self, wctrl):
        self.wctrl = wctrl
        self.model = wctrl.get_model()

    def resolve_color_spec(self, color_spec):
        return color_spec

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
        return selection, (tsum - csum)

    def make_etx_spec(self, our, their):
        our_color_set = self.resolve_color_spec(our['color_spec'])
        their_color_set = self.resolve_color_spec(their['color_spec'])

        c_utxos, c_change = self.select_inputs(our_color_set, our['value'])

        inputs = {our['color_spec']: [utxo.get_outpoint() for utxo in c_utxos]}
        
        wam = self.model.get_wallet_address_manager()
        our_address = self.model.get_change_address(their_color_set)
        
        targets = [(our_address.get_address(), their['color_spec'], their['value'])]

        if c_change > 0:
            out_change_address = wam.get_change_address(our_color_set)
            targets.append((our_change_address.get_address(), our['color_set'], c_change))

        return ETxSpec(inputs, targets)
        
        
    def make_reply_tx(self, etx_spec, our, their):
        
        
        
