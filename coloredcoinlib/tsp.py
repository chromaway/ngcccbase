from colordef import OBColorDefinition, ColorDefinition, UNCOLORED_MARKER
from txspec import OperationalTxSpec

class ProxyOperationalTxSpec(OperationalTxSpec):
    def __init__(self, real, targets):
        self.real = real
        self.targets = targets

    def get_targets(self):
        return self.targets

    def select_coins(self, color_def, colorvalue):
        return self.real.select_coins(color_def, colorvalue)

    def get_change_addr(self, color_def):
        return self.real.get_change_addr(color_def)

    def get_required_fee(self, tx_size):
        return self.real.get_required_fee(tx_size)


class DataScriptTarget(object):
    def __init__(self, data):
        self.data = data

class TSPColorDefinition(OBColorDefinition):
    CLASS_CODE = 'tsp'

    @classmethod
    def compose_genesis_tx_spec(cls, op_tx_spec):
        gen_targets = op_tx_spec.get_targets()[:]
        if len(gen_targets) != 1:
            raise Exception(
                'genesis transaction spec needs exactly one target')
        target_addr, color_def, value = gen_targets[0]

        unit = value[0]
        label = value[1]

        targets = [(target_addr, color_def, unit),
                   (DataScriptTarget(label), UNCOLORED_MARKER, 0)]

        return color_def.compose_tx_spec(ProxyOperationalTxSpec(op_tx_spec, targets))

ColorDefinition.register_color_def_class(TSPColorDefinition)
