""" Color definition schemes """

import txspec
from collections import defaultdict


def get_color_desc_code(color_desc):
    return color_desc.split(':')[0]


class ColorDefinition(object):
    """ Represents a color definition scheme.
    This means how color exists and is transferred
    in the blockchain"""
    cd_classes = {}
    CLASS_CODE = None

    def __init__(self, color_id):
        self.color_id = color_id

    def is_special_tx(self, tx):
        return False

    def run_kernel(self, tx, in_colorvalues):
        """ Applies color scheme to a certain transaction
        to obtain outputs' color values. """
        out_colorvalues = []
        for _ in tx.outputs:
            out_colorvalues.append(None)
        return out_colorvalues

    @classmethod
    def get_class_code(cls):
        return cls.CLASS_CODE

    @staticmethod
    def register_color_def_class(cdclass):
        ColorDefinition.cd_classes[cdclass.get_class_code()] = cdclass

    @classmethod
    def from_color_desc(cls, color_id, color_desc):
        code = get_color_desc_code(color_desc)
        cdclass = cls.cd_classes[code]
        return cdclass.from_color_desc(color_id, color_desc)

    @classmethod
    def get_color_def_cls_for_code(cls, code):
        return cls.cd_classes.get(code, None)

    def __repr__(self):
        return "%s" % self.color_id

GENESIS_OUTPUT_MARKER = ColorDefinition(-1)
UNCOLORED_MARKER = ColorDefinition(0)


class OBColorDefinition(ColorDefinition):
    """Implements order-based coloring scheme"""
    CLASS_CODE = 'obc'

    def __init__(self, color_id, genesis):
        super(OBColorDefinition, self).__init__(color_id)
        self.genesis = genesis

    def __repr__(self):
        return "%s:%s:%s:%s" % (
            self.CLASS_CODE, self.genesis['txhash'], self.genesis['outindex'],
            self.genesis['height'])

    def is_special_tx(self, tx):
        return tx.hash == self.genesis['txhash']

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

    def get_affecting_inputs(self, tx, output_set):
        """Returns a set object consisting of inputs that correspond to the
        output indexes of <output_set> from transaction <tx>
        """
        if self.is_special(tx):
            return set()
        tx.ensure_input_values()
        running_sum_inputs = []
        current_sum = 0
        for txin in tx.inputs:
            current_sum += txin.value
            running_sum_inputs.append(current_sum)
        running_sum_outputs = []
        current_sum = 0
        for output in tx.outputs:
            current_sum += output.value
            running_sum_outputs.append(current_sum)

        matching_input_set = set()

        num_inputs = len(running_sum_inputs)
        num_outputs = len(running_sum_outputs)
        for i in output_set:
            for j in range(num_inputs):
                if (i + 1 == num_outputs
                    or running_sum_inputs[j] < running_sum_outputs[i + 1]) \
                    and \
                    (j + 1 == num_inputs
                     or running_sum_outputs[i] < running_sum_inputs[j + 1]):
                    matching_input_set.add(tx.inputs[j])
        return matching_input_set

    @classmethod
    def compose_genesis_tx_spec(self, op_tx_spec):
        targets = op_tx_spec.get_targets()[:]
        if len(targets) != 1:
            raise Exception(
                'genesis transaction spec needs exactly one target')
        target_addr, color_def, value = targets[0]
        if color_def != GENESIS_OUTPUT_MARKER:
            raise Exception(
                'genesis transaction target should use -1 color_id')
        fee = op_tx_spec.get_required_fee(300)
        inputs, total = op_tx_spec.select_coins(UNCOLORED_MARKER, fee + value)
        change = total - fee - value
        if change > 0:
            targets.append((op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                            UNCOLORED_MARKER, change))
        txouts = [txspec.ComposedTxSpec.TxOut(target[2], target[0])
                  for target in targets]
        return txspec.ComposedTxSpec(inputs, txouts)

    def compose_tx_spec(self, op_tx_spec):
        targets_by_color = defaultdict(list)
        uncolored_targets = []
        # group targets by color
        for target in op_tx_spec.get_targets():
            color_def = target[1]
            if color_def == UNCOLORED_MARKER:
                uncolored_targets.append(target)
            elif isinstance(color_def, OBColorDefinition):
                targets_by_color[color_def.color_id].append(target)
            else:
                raise Exception('incompatible color definition')
        # get inputs for each color
        colored_inputs = []
        colored_targets = []
        for color_id, targets in targets_by_color.items():
            color_def = targets[0][1]
            needed_sum = sum([target[2] for target in targets])
            inputs, total = op_tx_spec.select_coins(color_def, needed_sum)
            change = total - needed_sum
            if change > 0:
                targets.append((op_tx_spec.get_change_addr(color_def),
                                color_def, change))
            colored_inputs += inputs
            colored_targets += targets
        uncolored_needed = sum([target[2] for target in uncolored_targets])
        fee = op_tx_spec.get_required_fee(250 * (len(colored_inputs) + 1))
        uncolored_inputs, uncolored_total = \
            op_tx_spec.select_coins(UNCOLORED_MARKER, uncolored_needed + fee)
        uncolored_change = uncolored_total - uncolored_needed - fee
        if uncolored_change > 0:
            uncolored_targets.append(
                (op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                 None, uncolored_change))
        txins = colored_inputs + uncolored_inputs
        txouts = [txspec.ComposedTxSpec.TxOut(target[2], target[0])
                  for target in (colored_targets + uncolored_targets)]
        return txspec.ComposedTxSpec(txins, txouts)

    @classmethod
    def from_color_desc(cls, color_id, color_desc):
        """ Create a color definition given a
        description string and the blockchain state"""
        code, txhash, outindex, height = color_desc.split(':')
        if (code != cls.CLASS_CODE):
            raise Exception('wrong color code in from_color_desc')
        genesis = {'txhash': txhash,
                   'height': int(height),
                   'outindex': int(outindex)}
        return cls(color_id, genesis)


class POBColorDefinition(ColorDefinition):

    CLASS_CODE = 'pobc'
    PADDING = 10000

    def __init__(self, color_id, genesis):
        super(POBColorDefinition, self).__init__(color_id)
        self.genesis = genesis

    def __repr__(self):
        return "%s:%s:%s:%s" % (
            self.CLASS_CODE, self.genesis['txhash'], self.genesis['outindex'],
            self.genesis['height'])

    def is_special_tx(self, tx):
        return tx.hash == self.genesis['txhash']

    def run_kernel(self, tx, in_colorvalues):
        """Computes the output colorvalues
        """

        is_genesis = (tx.hash == self.genesis['txhash'])

        # it turns out having a running sum in an array is easier
        #  than constructing segments
        input_running_sums = []
        running_sum = 0
        tx.ensure_input_values()
        for element in tx.inputs:
            colorvalue = self.satoshi_to_color(element.value)
            if colorvalue <= 0:
                break
            running_sum += colorvalue
            input_running_sums.append(running_sum)

        output_running_sums = []
        running_sum = 0
        for element in tx.outputs:
            colorvalue = self.satoshi_to_color(element.value)
            if colorvalue <= 0:
                break
            running_sum += colorvalue
            output_running_sums.append(running_sum)

        # default is that every output has a null colorvalue
        out_colorvalues = [None for i in output_running_sums]

        # see if this is a genesis transaction
        if is_genesis:
            # adjust the single genesis index to have the right value
            #  and return it
            i = self.genesis['outindex']
            out_colorvalues[i] = (self.satoshi_to_color(tx.outputs[i].value),
                                  '')
            return out_colorvalues

        # determine if the in_colorvalues are well-formed:
        # after that, there should be some number of non-null values
        # if another null is hit, there should be no more non-null values
        nonnull_sequences = 0
        if in_colorvalues[0] is None:
            current_sequence_is_null = True
            input_color_start = None
        else:
            current_sequence_is_null = False
            input_color_start = 0
        input_color_end = None
        for i, colorvalue in enumerate(in_colorvalues):
            if colorvalue is not None and current_sequence_is_null:
                current_sequence_is_null = False
                input_color_start = i
            elif colorvalue is None and not current_sequence_is_null:
                current_sequence_is_null = True
                input_color_end = i - 1
                nonnull_sequences += 1
        if not current_sequence_is_null:
            nonnull_sequences += 1
            input_color_end = len(in_colorvalues) - 1

        if nonnull_sequences > 1:
            return out_colorvalues

        # now figure out which segments correspond in the output
        if input_color_start == 0:
            sum_before_sequence = 0
        else:
            sum_before_sequence = input_running_sums[input_color_start - 1]
        sum_after_sequence = input_running_sums[input_color_end]

        # the sum of the segment before the sequence must be equal
        #  as the sum of the sequence itself must also be equal
        if (sum_before_sequence != 0
            and sum_before_sequence not in output_running_sums) or \
                sum_after_sequence not in output_running_sums:
            # this means we don't have matching places to start and/or end
            return out_colorvalues

        # now we know exactly where the output color sequence should start
        #  and end
        if sum_before_sequence == 0:
            output_color_start = 0
        else:
            output_color_start = output_running_sums.index(
                sum_before_sequence) + 1
        output_color_end = output_running_sums.index(sum_after_sequence)

        # calculate what the color value at that point is
        for i in range(output_color_start, output_color_end + 1):
            previous_sum = 0 if i == 0 else output_running_sums[i - 1]
            out_colorvalues[i] = (output_running_sums[i] - previous_sum, '')

        return out_colorvalues

    @classmethod
    def satoshi_to_color(cls, satoshivalue):
        return satoshivalue - cls.PADDING

    @classmethod
    def color_to_satoshi(cls, colorvalue):
        return colorvalue + cls.PADDING

    @classmethod
    def compose_genesis_tx_spec(cls, op_tx_spec):
        targets = op_tx_spec.get_targets()[:]
        if len(targets) != 1:
            raise Exception(
                'genesis transaction spec needs exactly one target')
        target_addr, color_def, colorvalue = targets[0]
        if color_def != GENESIS_OUTPUT_MARKER:
            raise Exception(
                'genesis transaction target should use -1 color_id')
        fee = op_tx_spec.get_required_fee(300)
        satoshivalue = cls.color_to_satoshi(colorvalue)
        # select uncolored coins to create the genesis
        inputs, total = op_tx_spec.select_coins(
            UNCOLORED_MARKER, fee + satoshivalue)
        change = total - fee - satoshivalue
        txouts = [
            txspec.ComposedTxSpec.TxOut(satoshivalue, target_addr)]
        if change > 0:
            txouts.append(
                txspec.ComposedTxSpec.TxOut(
                    change, op_tx_spec.get_change_addr(UNCOLORED_MARKER)))

        return txspec.ComposedTxSpec(inputs, txouts)

    def compose_tx_spec(self, op_tx_spec):
        # group targets by color
        targets_by_color = defaultdict(list)
        for target in op_tx_spec.get_targets():
            color_def = target[1]
            targets_by_color[color_def.color_id].append(target)
        uncolored_targets = targets_by_color.pop(UNCOLORED_MARKER.color_id, [])

        # get inputs for each color
        colored_inputs = []
        colored_targets = []
        for color_id, targets in targets_by_color.items():
            color_def = targets[0][1]
            needed_sum = sum([target[2] for target in targets])
            inputs, total = op_tx_spec.select_coins(color_def, needed_sum)
            change = total - needed_sum
            if change > 0:
                targets.append((op_tx_spec.get_change_addr(color_def),
                                color_def, change))
            colored_inputs += inputs
            colored_targets += targets

        # we also need some amount of extra "uncolored" coins
        # for padding purposes, possibly
        padding_needed = (len(colored_targets) - len(colored_inputs)) \
            * self.PADDING
        uncolored_needed = sum([target[2] for target in uncolored_targets]) \
            + padding_needed
        fee = op_tx_spec.get_required_fee(250 * (len(colored_inputs) + 1))
        amount_needed = uncolored_needed + fee
        if amount_needed == 0:
            uncolored_change = 0
            uncolored_inputs = []
        else:
            uncolored_inputs, uncolored_total = \
                op_tx_spec.select_coins(UNCOLORED_MARKER, amount_needed)
            uncolored_change = uncolored_total - amount_needed
        if uncolored_change > 0:
            uncolored_targets.append(
                (op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                 None, uncolored_change))

        # compose the TxIn and TxOut elements
        txins = colored_inputs + uncolored_inputs
        txouts = [
            txspec.ComposedTxSpec.TxOut(
                self.color_to_satoshi(target[2]), target[0])
            for target in colored_targets]
        txouts += [txspec.ComposedTxSpec.TxOut(target[2], target[0])
                   for target in uncolored_targets]
        return txspec.ComposedTxSpec(txins, txouts)

    @classmethod
    def from_color_desc(cls, color_id, color_desc):
        """ Create a color definition given a
        description string and the blockchain state"""
        code, txhash, outindex, height = color_desc.split(':')
        if (code != cls.CLASS_CODE):
            raise Exception('wrong color code in from_color_desc')
        genesis = {'txhash': txhash,
                   'height': int(height),
                   'outindex': int(outindex)}
        return cls(color_id, genesis)

ColorDefinition.register_color_def_class(OBColorDefinition)
ColorDefinition.register_color_def_class(POBColorDefinition)

if __name__ == "__main__":
    # test the POBC color kernel
    class MockTXElement:
        def __init__(self, value):
            self.value = value

    class MockTX:
        def __init__(self, hash, inputs, outputs):
            self.hash = hash
            self.inputs = [MockTXElement(i) for i in inputs]
            self.outputs = [MockTXElement(i) for i in outputs]

        def ensure_input_values(self):
            pass

    pobc = POBColorDefinition(
        "testcolor", {'txhash': 'genesis', 'outindex': 0})

    def test(inputs, outputs, in_colorvalue, txhash="not genesis"):
        tx = MockTX(txhash, inputs, outputs)
        return [i and i[0] for i in pobc.run_kernel(tx, in_colorvalue)]

    # genesis
    assert test([10001], [10001], [1], "genesis") == [1]
    assert test([40001], [10001, 30000], [1], "genesis") == [1, None]
    assert test([10000, 1], [10001], [1], "genesis") == [1]
    pobc.genesis['outindex'] = 1
    assert test([40001], [30000, 10001], [1], "genesis") == [None, 1]
    pobc.genesis['outindex'] = 0

    # simple transfer
    assert test([10001], [10001], [1]) == [1]
    # canonical split
    assert test([10002, 10003], [10005], [2, 3]) == [5]
    # canonical combine
    assert test([10005], [10002, 10003], [5]) == [2, 3]
    # null values before and after
    assert test([10001, 10002, 10003, 50000], [10001, 10005, 50000],
                [None, 2, 3, None]) == [None, 5, None]
    # ignore below-padding values
    assert test([10001, 10002, 10003, 50000, 100, 20000],
                [10001, 10005, 100, 70000, 100],
                [None, 2, 3, None]) == [None, 5]
    # color values don't add up the same
    assert test([10001, 10002, 10003, 10001, 50000], [10001, 10005, 50001],
                [None, 2, 3, 1, None]) == [None, None, None]
    # value before is not the same
    assert test([10001, 10002, 10003, 50000], [10002, 10005, 49999],
                [None, 2, 3, None]) == [None, None, None]
    # nonnull color values are not adjacent
    assert test([10001, 10002, 10003, 10004, 50000], [10001, 10006, 49999],
                [None, 2, None, 4, None]) == [None, None, None]
    # sequence before don't add up the same
    assert test([10005, 10001, 10002, 10003, 50000],
                [10004, 10001, 10005, 40000],
                [None, None, 2, 3, None]) == [None, None, None, None]
    # sequence before does add up the same
    assert test([10005, 10001, 10002, 10003, 50001],
                [10005, 10001, 10005, 40000],
                [None, None, 2, 3, None]) == [None, None, 5, None]
    # split to many
    assert test([10005, 10001, 10005, 50001],
                [10005, 10001, 10001, 10001, 10001, 10001, 10001, 40000],
                [None, None, 5, None]) == [None, None, 1, 1, 1, 1, 1, None]
    # combine many
    assert test([10005, 10001, 10001, 10001, 10001, 10001, 10001, 40000],
                [10005, 10001, 10005, 50001],
                [None, None, 1, 1, 1, 1, 1, None]) == [None, None, 5, None]
    # split and combine
    assert test([10001, 10002, 10003, 10004, 10005, 10006, 50000],
                [10001, 10005, 10009, 10006, 50000],
                [None, 2, 3, 4, 5, 6, None]) == [None, 5, 9, 6, None]
    # combine and split
    assert test([10005, 10009, 10006, 50000],
                [10002, 10003, 10004, 10005, 10006, 50000],
                [5, 9, 6, None]) == [2, 3, 4, 5, 6, None]
