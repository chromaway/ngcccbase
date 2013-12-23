""" Color definition schemes """

import txspec
import math
from collections import defaultdict

from colorvalue import SimpleColorValue
from txspec import ColorTarget


class InvalidTargetError(Exception):
    pass


class InvalidColorError(Exception):
    pass


class InvalidColorDefinitionError(Exception):
    pass


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

    def get_color_id(self):
        return self.color_id

    def is_special_tx(self):
        raise Exception("Implement is_special_tx method")  # pragma: no cover

    def run_kernel(self, tx, in_colorvalues):
        raise Exception("Implement run_kernel method")  # pragma: no cover

    @classmethod
    def color_to_satoshi(cls, colorvalue):
        return colorvalue.get_value()

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
        if self.color_id == 0:
            return ""
        elif self.color_id == -1:
            return "Genesis"
        return "Color Definition with %s" % self.color_id


GENESIS_OUTPUT_MARKER = ColorDefinition(-1)
UNCOLORED_MARKER = ColorDefinition(0)


class GenesisColorDefinition(ColorDefinition):

    def __init__(self, color_id, genesis):
        super(GenesisColorDefinition, self).__init__(color_id)
        self.genesis = genesis

    def __repr__(self):
        return "%s:%s:%s:%s" % (
            self.CLASS_CODE, self.genesis['txhash'], self.genesis['outindex'],
            self.genesis['height'])

    def is_special_tx(self, tx):
        return tx.hash == self.genesis['txhash']

    def satoshi_to_color(self, satoshivalue):
        return SimpleColorValue(colordef=self,
                                value=satoshivalue)

    @classmethod
    def from_color_desc(cls, color_id, color_desc):
        """ Create a color definition given a
        description string and the blockchain state"""
        code, txhash, outindex, height = color_desc.split(':')
        if (code != cls.CLASS_CODE):
            raise InvalidColorError('wrong color code in from_color_desc')
        genesis = {'txhash': txhash,
                   'height': int(height),
                   'outindex': int(outindex)}
        return cls(color_id, genesis)


class OBColorDefinition(GenesisColorDefinition):
    """Implements order-based coloring scheme"""
    CLASS_CODE = 'obc'

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
                cv = SimpleColorValue(colordef=self, value=o.value)
                out_colorvalues.append(cv)
            else:
                out_colorvalues.append(None)
        return out_colorvalues

    def get_affecting_inputs(self, tx, output_set):
        """Returns a set object consisting of inputs that correspond to the
        output indexes of <output_set> from transaction <tx>
        """
        if self.is_special_tx(tx):
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
        for o in output_set:
            if o == 0:
                o_start = 0
            else:
                o_start = running_sum_outputs[o-1]
            o_end = running_sum_outputs[o]
            for i in range(num_inputs):
                if i == 0:
                    i_start = 0
                else:
                    i_start = running_sum_inputs[i - 1]
                i_end = running_sum_inputs[i]
                # if segments overlap
                if (o_start < i_end and i_end <= o_end) \
                        or (i_start < o_end and o_end <= i_end):
                    matching_input_set.add(tx.inputs[i])
        return matching_input_set

    @classmethod
    def compose_genesis_tx_spec(self, op_tx_spec):
        targets = op_tx_spec.get_targets()[:]
        if len(targets) != 1:
            raise InvalidTargetError(
                'genesis transaction spec needs exactly one target')
        target = targets[0]
        if target.get_colordef() != GENESIS_OUTPUT_MARKER:
            raise InvalidColorError(
                'genesis transaction target should use -1 color_id')
        fee = op_tx_spec.get_required_fee(300)
        uncolored_value = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=target.get_value())
        colorvalue = fee + uncolored_value
        inputs, total = op_tx_spec.select_coins(colorvalue)
        change = total - fee - uncolored_value
        if change > 0:
            targets.append(ColorTarget(
                    op_tx_spec.get_change_addr(UNCOLORED_MARKER), change))
        txouts = [txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                              target.get_address())
                  for target in targets]
        return txspec.ComposedTxSpec(inputs, txouts)

    def compose_tx_spec(self, op_tx_spec):
        targets_by_color = defaultdict(list)
        uncolored_targets = []
        # group targets by color
        for target in op_tx_spec.get_targets():
            color_def = target.get_colordef()
            if color_def == UNCOLORED_MARKER:
                uncolored_targets.append(target)
            elif isinstance(color_def, OBColorDefinition):
                targets_by_color[color_def.color_id].append(target)
            else:
                raise InvalidColorError('incompatible color definition')
        # get inputs for each color
        colored_inputs = []
        colored_targets = []
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            needed_sum = ColorTarget.sum(targets)
            inputs, total = op_tx_spec.select_coins(needed_sum)
            change = total - needed_sum
            if change > 0:
                targets.append(
                    ColorTarget(op_tx_spec.get_change_addr(color_def), change))
            colored_inputs += inputs
            colored_targets += targets
        uncolored_needed = ColorTarget.sum(uncolored_targets)
        fee = op_tx_spec.get_required_fee(250 * (len(colored_inputs) + 1))
        uncolored_inputs, uncolored_total = op_tx_spec.select_coins(uncolored_needed + fee)
        uncolored_change = uncolored_total - uncolored_needed - fee
        if uncolored_change > 0:
            uncolored_targets.append(
                ColorTarget(op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                            uncolored_change))
        txins = colored_inputs + uncolored_inputs
        txouts = [txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                              target.get_address())
                  for target in (colored_targets + uncolored_targets)]
        return txspec.ComposedTxSpec(txins, txouts)


class POBColorDefinition(GenesisColorDefinition):

    CLASS_CODE = 'pobc'
    PADDING = 10000

    def run_kernel(self, tx, in_colorvalues):
        """Computes the output colorvalues"""

        is_genesis = (tx.hash == self.genesis['txhash'])

        # it turns out having a running sum in an array is easier
        #  than constructing segments
        input_running_sums = []
        ZERO_COLORVALUE = SimpleColorValue(colordef=self, value=0)
        running_sum = ZERO_COLORVALUE.clone()
        tx.ensure_input_values()
        for element in tx.inputs:
            colorvalue = self.satoshi_to_color(element.value)
            if colorvalue <= ZERO_COLORVALUE:
                break
            running_sum += colorvalue
            input_running_sums.append(running_sum.clone())

        output_running_sums = []
        running_sum = ZERO_COLORVALUE.clone()
        for element in tx.outputs:
            colorvalue = self.satoshi_to_color(element.value)
            if colorvalue <= ZERO_COLORVALUE:
                break
            running_sum += colorvalue
            output_running_sums.append(running_sum.clone())

        # default is that every output has a null colorvalue
        out_colorvalues = [None for i in output_running_sums]

        # see if this is a genesis transaction
        if is_genesis:
            # adjust the single genesis index to have the right value
            #  and return it
            i = self.genesis['outindex']
            out_colorvalues[i] = self.satoshi_to_color(tx.outputs[i].value)
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
            sum_before_sequence = ZERO_COLORVALUE.clone()
        else:
            sum_before_sequence = input_running_sums[input_color_start - 1]
        sum_after_sequence = input_running_sums[input_color_end]

        # the sum of the segment before the sequence must be equal
        #  as the sum of the sequence itself must also be equal
        if (sum_before_sequence != ZERO_COLORVALUE
            and sum_before_sequence not in output_running_sums) or \
                sum_after_sequence not in output_running_sums:
            # this means we don't have matching places to start and/or end
            return out_colorvalues

        # now we know exactly where the output color sequence should start
        #  and end
        if sum_before_sequence == ZERO_COLORVALUE:
            output_color_start = 0
        else:
            output_color_start = output_running_sums.index(
                sum_before_sequence) + 1
        output_color_end = output_running_sums.index(sum_after_sequence)

        # calculate what the color value at that point is
        for i in range(output_color_start, output_color_end + 1):
            previous_sum = ZERO_COLORVALUE if i == 0 \
                else output_running_sums[i - 1]
            out_colorvalues[i] = output_running_sums[i] - previous_sum

        return out_colorvalues

    def satoshi_to_color(self, satoshivalue):
        return SimpleColorValue(colordef=self,
                                value=satoshivalue - self.PADDING)

    @classmethod
    def color_to_satoshi(cls, colorvalue):
        return colorvalue.get_value() + cls.PADDING

    @classmethod
    def compose_genesis_tx_spec(cls, op_tx_spec):
        targets = op_tx_spec.get_targets()[:]
        if len(targets) != 1:
            raise InvalidTargetError(
                'genesis transaction spec needs exactly one target')
        target = targets[0]
        if target.get_colordef() != GENESIS_OUTPUT_MARKER:
            raise InvalidColorError(
                'genesis transaction target should use -1 color_id')
        fee = op_tx_spec.get_required_fee(300)
        amount = target.colorvalue.get_satoshi()
        uncolored_value = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=amount)
        colorvalue = fee + uncolored_value
        inputs, total = op_tx_spec.select_coins(colorvalue)
        change = total - fee - uncolored_value
        if change > 0:
            targets.append(ColorTarget(
                    op_tx_spec.get_change_addr(UNCOLORED_MARKER), change))
        txouts = [txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                              target.get_address())
                  for target in targets]
        return txspec.ComposedTxSpec(inputs, txouts)

    def compose_tx_spec(self, op_tx_spec):
        # group targets by color
        targets_by_color = defaultdict(list)
        # group targets by color
        for target in op_tx_spec.get_targets():
            color_def = target.get_colordef()
            if color_def == UNCOLORED_MARKER \
                    or isinstance(color_def, POBColorDefinition):
                targets_by_color[color_def.color_id].append(target)
            else:
                raise InvalidColorError('incompatible color definition')
        uncolored_targets = targets_by_color.pop(UNCOLORED_MARKER.color_id, [])

        # get inputs for each color
        colored_inputs = []
        colored_targets = []
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            needed_sum = ColorTarget.sum(targets)
            inputs, total = op_tx_spec.select_coins(needed_sum)
            change = total - needed_sum
            if change > 0:
                targets.append(ColorTarget(
                        op_tx_spec.get_change_addr(color_def), change))
            colored_inputs += inputs
            colored_targets += targets

        # we also need some amount of extra "uncolored" coins
        # for padding purposes, possibly
        padding_needed = (len(colored_targets) - len(colored_inputs)) \
            * self.PADDING
        uncolored_needed = ColorTarget.sum(uncolored_targets) \
            + SimpleColorValue(colordef=UNCOLORED_MARKER, value=padding_needed)
        fee = op_tx_spec.get_required_fee(250 * (len(colored_inputs) + 1))
        amount_needed = uncolored_needed + fee
        zero = SimpleColorValue(colordef=UNCOLORED_MARKER, value=0)
        if amount_needed == zero:
            uncolored_change = zero
            uncolored_inputs = []
        else:
            uncolored_inputs, uncolored_total = op_tx_spec.select_coins(amount_needed)
            uncolored_change = uncolored_total - amount_needed
        if uncolored_change > zero:
            uncolored_targets.append(
                ColorTarget(op_tx_spec.get_change_addr(UNCOLORED_MARKER),
                 uncolored_change))

        # compose the TxIn and TxOut elements
        txins = colored_inputs + uncolored_inputs
        txouts = [
            txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                        target.get_address())
            for target in colored_targets]
        txouts += [txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                               target.get_address())
                   for target in uncolored_targets]
        return txspec.ComposedTxSpec(txins, txouts)


def ones(n):
    """ finds indices for the 1's in an integer"""
    while n:
        b = n & (~n + 1)
        i = int(math.log(b, 2))
        yield i
        n ^= b
   
class BFTColorDefinition (GenesisColorDefinition):
    CLASS_CODE = 'btfc'

    def run_kernel(self, tx, in_colorvalues):
        """Computes the output colorvalues"""
        # special case: genesis tx output
        tx.ensure_input_values()
        if tx.hash == self.genesis['txhash']:
            return [SimpleColorValue(colordef=self, value=out.value)
                    if self.genesis['outindex'] == i else None \
                        for i, out in enumerate(tx.outputs)]
            
        # start with all outputs having null colorvalue
        nones = [None for _ in tx.outputs]
        out_colorvalues = [None for _ in tx.outputs]
        output_groups = {}
        # go through all inputs
        for inp_index in xrange(len(tx.inputs)):
            # if input has non-null colorvalue, check its nSequence
            color_value = in_colorvalues[inp_index]
            if color_value:
                nSequence = tx.raw.vin[inp_index].nSequence
                # nSequence is converted to a set of output indices
                output_group = list(ones(nSequence))
                
                # exceptions; If exceptional situation is detected, we return a list of null colorvalues.
                # nSequence is 0
                if nSequence == 0:
                    return nones
                
                # nSequence has output indices exceeding number of outputs of this transactions
                for out_idx in output_group:
                    if out_idx >= len(tx.inputs):
                        return nones
                # there are intersecting 'output groups' (i.e output belongs to more than one group)
                if not nSequence in output_groups:
                    for og in output_groups:
                        if len(set(ones(og)).intersection(output_group)) != 0:
                            return nones
                    output_groups[nSequence] = SimpleColorValue(colordef=self,
                                                                value=0)
                        
                # add colorvalue of this input to colorvalue of output group
                output_groups[nSequence] += color_value

        # At this step we have total colorvalue for each output group.
        # For each output group:
        for nSequence in output_groups:
            output_group = list(ones(nSequence))
            in_colorvalue = output_groups[nSequence]
            # sum satoshi-values of outputs in it (let's call it ssvalue)
            ssvalue = sum(tx.outputs[out_idx].value for out_idx in output_group)
            #find n such that 2^n*ssvalue = total colorvalue (loop over all |n|<32, positive and negative)
            for n in xrange(-31,32):
                if ssvalue*2**n == in_colorvalue.get_value():
                    # if n exists, each output of this group is assigned colorvalue svalue*2^n, where svalue is its satoshi-value
                    for out_idx in output_group:
                        svalue = tx.outputs[out_idx].value
                        out_colorvalues[out_idx] = SimpleColorValue(colordef=self, value=svalue*2**n, label=in_colorvalue.get_label())
                    break
            else:
                # if n doesn't exist, we treat is as an exceptional sitation and return a list of None values.
                return nones  # pragma: no cover

        return out_colorvalues

ColorDefinition.register_color_def_class(OBColorDefinition)
ColorDefinition.register_color_def_class(POBColorDefinition)
ColorDefinition.register_color_def_class(BFTColorDefinition)
