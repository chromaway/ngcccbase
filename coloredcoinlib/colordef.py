def get_color_desc_code(color_desc):
    return color_desc.split(':')[0]

class ColorDefinition(object):
    cd_classes = {}

    def __init__(self, color_id):
        self.color_id = color_id
        self.starting_height = None

    def is_special_tx(self, tx):
        return False

    def run_kernel(self, tx, in_colorstates):
        out_colorstates = []
        for o in tx.outputs:
            out_colorstates.append(None)
        return out_colorstates

    @staticmethod
    def register_color_def_class(code, class):
        ColorDefinition.cd_classes[code] = class

    @classmethod
    def from_color_desc(cdc, color_id, color_desc):
        code = get_color_desc_class(color_desc)
        cdclass = cdc.cd_classes[code]
        cdclass.from_color_desc(color_id, color_desc)
        

class OBColorDefinition(ColorDefinition):
    class_code = 'obc'
    ColorDefinition.register_color_def_class(class_code, OBColorDefinition)

    def __init__(self, color_id, genesis):
        super(OBColorDefinition, self).__init__(color_id)
        self.genesis = genesis
        self.starting_height = genesis['height']

    def is_special_tx(self, tx):
        return (tx.hash == self.genesis['txhash'])

    def run_kernel(self, tx, in_colorstates):
        out_colorstates = []
        inp_index = 0
        cur_value = 0
        colored = False

        is_genesis = (tx.hash == self.genesis['txhash'])

        tx.ensure_input_values()

        for out_index in xrange(len(tx.outputs)):
            o = tx.outputs[out_index]
            if cur_value == 0:
                colored = True # reset
            while cur_value < o.value:
                cur_value += tx.inputs[inp_index].value
                if colored:
                    colored = (in_colorstates[inp_index] != None)
                inp_index += 1

            # genesis override:
            if is_genesis and (out_index == self.genesis['outindex']):
                colored = True

            if colored:
                out_colorstates.append((o.value, ''))
            else:
                out_colorstates.append(None)
        return out_colorstates
        
    @classmethod
    def from_color_desc(cdc, color_id, color_desc):
        code, txhash, outindex, height = color_desc.split(':')
        if (code != class_code):
            raise Exception('wrong color code in from_color_desc')
        genesis = {'txhash': txhash,
                   'height': int(height),
                   'outindex': int(outindex)}
        return cdc(colorid, genesis)
        
