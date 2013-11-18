import txspec
from collections import defaultdict


def get_color_desc_code(color_desc):
    return color_desc.split(':')[0]


class ColorDefinition(object):
    cd_classes = {}

    def __init__(self, color_id):
        self.color_id = color_id

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
    def from_color_desc(cdc, color_id, color_desc, blockchain_state):
        code = get_color_desc_code(color_desc)
        cdclass = cdc.cd_classes[code]
        return cdclass.from_color_desc(color_id, color_desc, blockchain_state)

    def __repr__(self):
        return "%s" % self.color_id

genesis_output_marker = ColorDefinition(-1)

class OBColorDefinition(ColorDefinition):
    """Implements order-based coloring"""
    class_code = 'obc'

    def __init__(self, color_id, genesis):
        super(OBColorDefinition, self).__init__(color_id)
        self.genesis = genesis

    def __repr__(self):
        return "%s:%s:%s:%s" % (
            self.class_code, self.genesis['txhash'], self.genesis['outindex'],
            self.genesis['height'])

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
        target_addr, color_def, value = targets[0]
        if color_def != genesis_output_marker:
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
        targets_by_color = defaultdict(list)
        uncolored_targets = []
        # group targets by color
        for target in op_tx_spec.get_targets():
            color_def = target[1]
            if color_def is None:
                uncolored_targets.append(target)
            elif isinstance(color_def, OBColorDefinition):
                targets_by_color[color_def.color_id].append(target)
            else:
                raise Exception('incompatible color definition')
        # get inputs for each color
        colored_inputs = []
        colored_targets = []
        for color_id, targets in targets_by_color.items():
            needed_sum = sum([target[2] for target in targets])
            inputs, total = op_tx_spec.select_coins(color_id, needed_sum)
            change = total - needed_sum
            if change > 0:
                targets.append((op_tx_spec.get_change_addr(color_id),
                                targets[0][1], change))
            colored_inputs += inputs
            colored_targets += targets
        uncolored_needed = sum([target[2] for target in uncolored_targets])
        fee = op_tx_spec.get_required_fee(250*(len(colored_inputs) + 1))
        uncolored_inputs, uncolored_total = \
            op_tx_spec.select_coins(0, uncolored_needed + fee)
        uncolored_change = uncolored_total - uncolored_needed - fee
        if uncolored_change > 0:
            uncolored_targets.append(
                (op_tx_spec.get_change_addr(0), None, uncolored_change))
        txins = [txspec.ComposedTxSpec.TxIn(utxo) for utxo in
                 (colored_inputs + uncolored_inputs)]
        txouts = [txspec.ComposedTxSpec.TxOut(target[2], target[0])
                  for target in (colored_targets + uncolored_targets)]
        return txspec.ComposedTxSpec(txins, txouts)

    @classmethod
    def from_color_desc(cdc, color_id, color_desc, blockchain_state):
        code, txhash, outindex, height = color_desc.split(':')

        if (code != cdc.class_code):
            raise Exception('wrong color code in from_color_desc')
        blockhash = blockchain_state.get_tx_blockhash(txhash)
        genesis = {'txhash': txhash,
                   'height': int(height),
                   'blockhash': blockhash,
                   'outindex': int(outindex)}
        return cdc(color_id, genesis)

ColorDefinition.register_color_def_class(
    OBColorDefinition.class_code, OBColorDefinition)
