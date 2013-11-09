import txspec


def get_color_desc_code(color_desc):
    return color_desc.split(':')[0]


class ColorDefinition(object):
    cd_classes = {}

    def __init__(self, color_id):
        self.color_id = color_id
        self.starting_height = None

    def is_special_tx(self, tx):
        return False

    def run_kernel(self, tx, in_colorvalues):
        out_colorvalues = []
        for _ in tx.outputs:
            out_colorvalues.append(None)
        return out_colorvalues

    @staticmethod
    def register_color_def_class(code, clAss):
        ColorDefinition.cd_classes[code] = clAss

    @classmethod
    def from_color_desc(cdc, color_id, color_desc):
        code = get_color_desc_code(color_desc)
        cdclass = cdc.cd_classes[code]
        return cdclass.from_color_desc(color_id, color_desc)


class OBColorDefinition(ColorDefinition):
    """Implements order-based coloring"""
    class_code = 'obc'

    def __init__(self, color_id, genesis):
        super(OBColorDefinition, self).__init__(color_id)
        self.genesis = genesis
        self.starting_height = genesis['height']

    def is_special_tx(self, tx):
        return (tx.hash == self.genesis['txhash'])

    def run_kernel(self, tx, in_colorvalues):
        out_colorvalues = []
        inp_index = 0
        cur_value = 0
        colored = False

        is_genesis = (tx.hash == self.genesis['txhash'])

        tx.ensure_input_values()

        for out_index in xrange(len(tx.outputs)):
            o = tx.outputs[out_index]
            if cur_value == 0:
                colored = True  # reset
            while cur_value < o.value:
                cur_value += tx.inputs[inp_index].value
                if colored:
                    colored = (in_colorvalues[inp_index] is not None)
                inp_index += 1

            is_genesis_output = is_genesis and (
                out_index == self.genesis['outindex'])

            if colored or is_genesis_output:
                out_colorvalues.append((o.value, ''))
            else:
                out_colorvalues.append(None)
        return out_colorvalues

    @classmethod
    def compose_genesis_tx_spec(self, op_tx_spec):
        targets = op_tx_spec.get_targets()[:]
        if len(targets) != 1:
            raise Exception(
                'genesis transaction spec needs exactly one target')
        target_addr, color_id, value = targets[0]
        if color_id != -1:
            raise Exception(
                'genesis transaction target should use -1 color_id')
        fee = op_tx_spec.get_required_fee(300)
        inputs, total = op_tx_spec.select_coins(0, fee + value)
        change = total - fee - value
        if change > 0:
            targets.append((op_tx_spec.get_change_addr(0), 0, change))
        txins = [txspec.ComposedTxSpec.TxIn(utxo)
                 for utxo in inputs]
        txouts = [txspec.ComposedTxSpec.TxOut(target[2], target[0])
                  for target in targets]
        return txspec.ComposedTxSpec(txins, txouts)

    def compose_tx_spec(self, op_tx_spec):
        colored_targets = []
        uncolored_targets = []
        for target in op_tx_spec.get_targets():
            color_id = target[1]
            if color_id == self.color_id:
                colored_targets.append(target)
            elif color_id == 0:
                uncolored_targets.append(target)
            else:
                raise Exception('ColorDef cannot work with this color_id')
        colored_needed = sum([target[2] for target in colored_targets])
        uncolored_needed = sum([target[2] for target in uncolored_targets])
        colored_inputs, colored_total = op_tx_spec.select_coins(
            self.color_id, colored_needed)
        fee = op_tx_spec.get_required_fee(750)
        uncolored_inputs, uncolored_total = op_tx_spec.select_coins(
            0, uncolored_needed + fee)
        colored_change = colored_total - colored_needed
        if colored_change > 0:
            colored_targets.append(
                (op_tx_spec.get_change_addr(self.color_id),
                 self.color_id, colored_change))
        uncolored_change = uncolored_total - uncolored_needed - fee
        if uncolored_change > 0:
            uncolored_targets.append(
                (op_tx_spec.get_change_addr(0), 0, uncolored_change))
        txins = [txspec.ComposedTxSpec.TxIn(utxo) for utxo in
                 (colored_inputs + uncolored_inputs)]
        txouts = [txspec.ComposedTxSpec.TxOut(target[2], target[0])
                  for target in (colored_targets + uncolored_targets)]
        return txspec.ComposedTxSpec(txins, txouts)

    @classmethod
    def from_color_desc(cdc, color_id, color_desc):
        code, txhash, outindex, height = color_desc.split(':')
        if (code != cdc.class_code):
            raise Exception('wrong color code in from_color_desc')
        genesis = {'txhash': txhash,
                   'height': int(height),
                   'outindex': int(outindex)}
        return cdc(color_id, genesis)

ColorDefinition.register_color_def_class(
    OBColorDefinition.class_code, OBColorDefinition)
