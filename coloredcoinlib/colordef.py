""" Color definition schemes """

import txspec
import math
from collections import defaultdict

from colorvalue import SimpleColorValue
from txspec import ColorTarget

from logger import log

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

def group_targets_by_color(targets, compat_cls):
    # group targets by color
    targets_by_color = defaultdict(list)
    # group targets by color
    for target in targets:
        color_def = target.get_colordef()
        if color_def == UNCOLORED_MARKER \
                or isinstance(color_def, compat_cls):
            targets_by_color[color_def.color_id].append(target)
        else:
            raise InvalidColorError('incompatible color definition')
    return targets_by_color


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
        targets_by_color = group_targets_by_color(op_tx_spec.get_targets(), self.__class__)
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


def uint_to_bit_list(n, bits=32):
    """little-endian"""
    return [1 & (n >> i) for i in range(bits)]

def bit_list_to_uint(bits):
    number = 0
    factor = 1
    for b in bits:
        if b == 1:
            number += factor
        factor *= 2
    return number

class EPOBCColorDefinition(GenesisColorDefinition):
    CLASS_CODE = 'epobc'

    class Tag(object):
        XFER_TAG_BITS = [1, 1, 0, 0, 1, 1]
        GENESIS_TAG_BITS = [1, 0, 1, 0, 0, 1]
        def __init__(self, padding_code, is_genesis):
            self.is_genesis = is_genesis
            self.padding_code = padding_code

        @classmethod
        def closest_padding_code(cls, min_padding):
            if min_padding <= 0:
                return 0
            padding_code = 1
            while 2 ** padding_code < min_padding:
                padding_code += 1
            if padding_code > 63:
                raise Exception('requires too much padding')
            return padding_code

        @classmethod
        def from_nSequence(cls, nSequence):
            print nSequence
            bits = uint_to_bit_list(nSequence)
            tag_bits = bits[0:6]
            
            if ((tag_bits != cls.XFER_TAG_BITS) and
                (tag_bits != cls.GENESIS_TAG_BITS)):
                return None
            
            padding_code = bit_list_to_uint(bits[6:12])
            return cls(padding_code, tag_bits == cls.GENESIS_TAG_BITS)
        
        def to_nSequence(self):
            if self.is_genesis:
                bits = self.GENESIS_TAG_BITS[:]
            else:
                bits = self.XFER_TAG_BITS[:]
            bits += uint_to_bit_list(self.padding_code,
                                     6)
            bits += [0] * (32 - 12)
            return bit_list_to_uint(bits)

        def get_padding(self):
            if self.padding_code == 0:
                return 0
            else:
                return 2 ** self.padding_code

    @classmethod
    def get_tag(cls, tx):
        if tx.raw.vin[0].prevout.is_null():
            # coinbase tx is neither genesis nor xfer
            return None
        else:
            return cls.Tag.from_nSequence(tx.raw.vin[0].nSequence)

    @classmethod
    def get_xfer_affecting_inputs(cls, tx, padding, out_index):
        tx.ensure_input_values()
        out_prec_sum = 0
        for oi in range(out_index):
            value_wop = tx.outputs[oi].value - padding
            if value_wop <= 0:
                return set()
            out_prec_sum += value_wop
        out_value_wop = tx.outputs[out_index].value - padding
        if out_value_wop <= 0:
            return set()
        affecting_inputs = set()
        input_running_sum = 0
        for ii, inp in enumerate(tx.inputs):
            prev_tag = cls.get_tag(inp.prevtx)
            if not prev_tag:
                break
            value_wop = tx.inputs[ii].value - prev_tag.get_padding()
            if value_wop <= 0:
                break
            if ((input_running_sum < (out_prec_sum + out_value_wop)) and
                ((input_running_sum + value_wop) > out_prec_sum)):
                affecting_inputs.add(ii)
            input_running_sum += value_wop
        return affecting_inputs


    def run_kernel(self, tx, in_colorvalues):
        log("in_colorvalues: %s", in_colorvalues)
        tag = self.get_tag(tx)
        if tag is None:
            return [None] * len(tx.outputs)
        if tag.is_genesis:
            if tx.hash == self.genesis['txhash']:
                value_wop = tx.outputs[0].value - tag.get_padding()
                if value_wop > 0:
                    return ([SimpleColorValue(colordef=self,
                                              value=value_wop)] + 
                            [None] * (len(tx.outputs) - 1))
            # we get here if it is a genesis for a different color
            # or if genesis transaction is misconstructed
            return [None] * len(tx.outputs)

        tx.ensure_input_values()
        padding = tag.get_padding()
        out_colorvalues = []
        for out_idx, output in enumerate(tx.outputs):
            out_value_wop = tx.outputs[out_idx].value - padding
            if out_value_wop <= 0:
                out_colorvalues.append(None)
                continue
            affecting_inputs = self.get_xfer_affecting_inputs(tx, tag.get_padding(),
                                                              out_idx)
            log("affecting inputs: %s", affecting_inputs)
            ai_colorvalue = SimpleColorValue(colordef=self, value=0)
            all_colored = True
            for ai in affecting_inputs:
                if in_colorvalues[ai] is None:
                    all_colored = False
                    break
                ai_colorvalue += in_colorvalues[ai]
            log("all colored: %s, colorvalue:%s", all_colored, ai_colorvalue.get_value())
            if (not all_colored) or (ai_colorvalue.get_value() < out_value_wop):
                out_colorvalues.append(None)
                continue
            out_colorvalues.append(SimpleColorValue(colordef=self, value=out_value_wop))
        log("out_colorvalues: %s", out_colorvalues)
        return out_colorvalues

    def get_affecting_inputs(self, tx, output_set):
        tag = self.get_tag(tx)
        if (tag is None) or tag.is_genesis:
            return set()
        tx.ensure_input_values()
        aii = set()
        for out_idx in output_set:
            aii.update(self.get_xfer_affecting_inputs(
                    tx, tag.get_padding(), out_idx))
        inputs = set([tx.inputs[i] for i in aii])
        return inputs

    def compose_tx_spec(self, op_tx_spec):
        targets_by_color = group_targets_by_color(op_tx_spec.get_targets(), self.__class__)
        uncolored_targets = targets_by_color.pop(UNCOLORED_MARKER.color_id, [])
        colored_txins = []
        colored_txouts = []
        if uncolored_targets:
            uncolored_needed = ColorTarget.sum(uncolored_targets)
        else:
            uncolored_needed = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                                value=0)

        dust_threshold = op_tx_spec.get_dust_threshold().get_value()

        inputs_by_color = dict()

        min_padding = 0
        # step 1: get inputs, create change targets, compute min padding
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            needed_sum = ColorTarget.sum(targets)
            inputs, total = op_tx_spec.select_coins(needed_sum)
            inputs_by_color[color_id] = inputs
            change = total - needed_sum
            if change > 0:
                targets.append(
                    ColorTarget(op_tx_spec.get_change_addr(color_def), change))
            for target in targets:
                padding_needed = dust_threshold - target.get_value() 
                if padding_needed > min_padding:
                    min_padding = padding_needed

        tag = self.Tag(self.Tag.closest_padding_code(min_padding), False)
        padding = tag.get_padding()

        # step 2: create txins & txouts, compute uncolored requirements
        for color_id, targets in targets_by_color.items():
            color_def = targets[0].get_colordef()
            for inp in inputs_by_color[color_id]:
                colored_txins.append(inp)
                uncolored_needed -= SimpleColorValue(colordef=UNCOLORED_MARKER,
                                               value=inp.value)
                print uncolored_needed
            for target in targets:
                svalue = target.get_value() + padding
                colored_txouts.append(
                    txspec.ComposedTxSpec.TxOut(svalue,
                                                target.get_address()))
                uncolored_needed += SimpleColorValue(colordef=UNCOLORED_MARKER,
                                               value=svalue)
                print uncolored_needed

        fee = op_tx_spec.get_required_fee(250 * (len(colored_txins) + 1))

        uncolored_txouts = []
        uncolored_inputs = []
        uncolored_change = None

        if uncolored_needed + fee > 0:
            uncolored_inputs, uncolored_total = op_tx_spec.select_coins(uncolored_needed + fee)
            uncolored_txouts = [txspec.ComposedTxSpec.TxOut(target.get_satoshi(),
                                                            target.get_address())
                                for target in uncolored_targets]
            uncolored_change = uncolored_total - uncolored_needed - fee
        else:
            uncolored_change =  (- uncolored_needed) - fee
            
        if uncolored_change > 0:
            uncolored_txouts.append(txspec.ComposedTxSpec.TxOut(
                    uncolored_change.get_value(), 
                    op_tx_spec.get_change_addr(UNCOLORED_MARKER)))

        all_inputs = colored_txins + uncolored_inputs

        all_inputs[0].set_nSequence(tag.to_nSequence())

        return txspec.ComposedTxSpec(all_inputs,
                                     colored_txouts + uncolored_txouts)

    @classmethod
    def compose_genesis_tx_spec(cls, op_tx_spec):
        if len(op_tx_spec.get_targets()) != 1:
            raise InvalidTargetError(
                'genesis transaction spec needs exactly one target')
        g_target = op_tx_spec.get_targets()[0]
        if g_target.get_colordef() != GENESIS_OUTPUT_MARKER:
            raise InvalidColorError(
                'genesis transaction target should use -1 color_id')
        fee = op_tx_spec.get_required_fee(300)
        g_value = g_target.get_value()
        padding_needed = op_tx_spec.get_dust_threshold().get_value() - g_value
        tag = cls.Tag(cls.Tag.closest_padding_code(padding_needed), True)
        padding = tag.get_padding()
        uncolored_needed = SimpleColorValue(colordef=UNCOLORED_MARKER,
                                           value=padding + g_value)
        uncolored_inputs, uncolored_total = op_tx_spec.select_coins(uncolored_needed + fee)
        change = uncolored_total - uncolored_needed - fee

        txouts = []
        txouts.append(txspec.ComposedTxSpec.TxOut(padding + g_value,
                                                  g_target.get_address()))
        if change > 0:
            txouts.append(txspec.ComposedTxSpec.TxOut(
                    change.get_value(), op_tx_spec.get_change_addr(UNCOLORED_MARKER)))
        uncolored_inputs[0].set_nSequence(tag.to_nSequence())
        return txspec.ComposedTxSpec(uncolored_inputs, txouts)


ColorDefinition.register_color_def_class(OBColorDefinition)
ColorDefinition.register_color_def_class(EPOBCColorDefinition)
