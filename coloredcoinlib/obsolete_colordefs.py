# NOTE: these colordefs are unused, untested,
#       and will be deleted in later released


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
                'Genesis transaction spec needs exactly one target!')
        target = targets[0]
        if target.get_colordef() != GENESIS_OUTPUT_MARKER:
            raise InvalidColorError(
                'Genesis transaction target should use -1 color_id!')
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
                raise InvalidColorError('Incompatible color definition!')
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

# ColorDefinition.register_color_def_class(POBColorDefinition)
# ColorDefinition.register_color_def_class(BFTColorDefinition)
