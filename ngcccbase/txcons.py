"""
txcons.py

Transaction Constructors for the blockchain.
"""

from asset import AssetTarget
from coloredcoinlib import (ColorSet, ColorTarget, SimpleColorValue,
                            ComposedTxSpec, OperationalTxSpec,
                            UNCOLORED_MARKER, OBColorDefinition,
                            InvalidColorIdError, ZeroSelectError)
from binascii import hexlify
import pycoin_txcons

import io


class InsufficientFundsError(Exception):
    pass


class InvalidTargetError(Exception):
    pass


class InvalidTransformationError(Exception):
    pass


class BasicTxSpec(object):
    """Represents a really simple colored coin transaction.
    Specifically, this particular transaction class has not been
    constructed, composed or signed. Those are done in other classes.
    Note this only supports a single asset.
    """
    def __init__(self, model):
        """Create a BasicTxSpec that has a wallet_model <model>
        for an asset <asset>
        """
        self.model = model
        self.targets = []

    def add_target(self, asset_target):
        """Add a ColorTarget <color_target> which specifies the
        colorvalue and address
        """
        if not isinstance(asset_target, AssetTarget):
            raise InvalidTargetError("Not an asset target")
        self.targets.append(asset_target)

    def is_monoasset(self):
        """Returns a boolean representing if the transaction sends
        coins of exactly 1 color.
        """
        if not self.targets:
            raise InvalidTargetError('basic txs is empty')
        asset = self.targets[0].get_asset()
        for target in self.targets:
            if target.get_asset() != asset:
                return False
        return True

    def is_monocolor(self):
        """Returns a boolean representing if the transaction sends
        coins of exactly 1 color.
        """
        if not self.is_monoasset():
            return False
        asset = self.targets[0].get_asset()
        return len(asset.get_color_set().color_id_set) == 1

    def make_operational_tx_spec(self, asset):
        """Given a <tx_spec> of type BasicTxSpec, return
        a SimpleOperationalTxSpec.
        """
        if not self.is_monocolor():
            raise InvalidTransformationError('tx spec type not supported')
        op_tx_spec = SimpleOperationalTxSpec(self.model, asset)
        color_id = list(asset.get_color_set().color_id_set)[0]
        color_def = self.model.get_color_def(color_id)
        for target in self.targets:
            colorvalue = SimpleColorValue(colordef=color_def,
                                          value=target.get_value())
            colortarget = ColorTarget(target.get_address(), colorvalue)
            op_tx_spec.add_target(colortarget)
        return op_tx_spec


class SimpleOperationalTxSpec(OperationalTxSpec):
    """Subclass of OperationalTxSpec which uses wallet model.
    Represents a transaction that's ready to be composed
    and then signed. The parent is an abstract class.
    """
    def __init__(self, model, asset):
        """Initialize a transaction that uses a wallet model
        <model> and transfers asset/color <asset>.
        """
        super(SimpleOperationalTxSpec, self).__init__()
        self.model = model
        self.targets = []
        self.asset = asset

    def add_target(self, color_target):
        """Add a ColorTarget <color_target> to the transaction
        """
        if not isinstance(color_target, ColorTarget):
            raise InvalidTargetError("Target is not an instance of ColorTarget")
        self.targets.append(color_target)

    def get_targets(self):
        """Get a list of (receiving address, color_id, colorvalue)
        triplets representing all the targets for this tx.
        """
        return self.targets

    def get_change_addr(self, color_def):
        """Get an address associated with color definition <color_def>
        that is in the current wallet for receiving change.
        """
        color_id = color_def.color_id
        wam = self.model.get_address_manager()
        color_set = None
        if color_def == UNCOLORED_MARKER:
            color_set = ColorSet.from_color_ids(self.model.get_color_map(),
                                                [0])
        elif self.asset.get_color_set().has_color_id(color_id):
            color_set = self.asset.get_color_set()
        if color_set is None:
            raise InvalidColorIdError('wrong color id')
        aw = wam.get_change_address(color_set)
        return aw.get_address()

    def select_coins(self, colorvalue):
        """Return a list of utxos and sum that corresponds to
        the colored coins identified by <color_def> of amount <colorvalue>
        that we'll be spending from our wallet.
        """
        colordef = colorvalue.get_colordef()
        color_id = colordef.get_color_id()
        cq = self.model.make_coin_query({"color_id_set": set([color_id])})
        utxo_list = cq.get_result()

        zero = ssum = SimpleColorValue(colordef=colordef, value=0)
        selection = []
        if colorvalue == zero:
            raise ZeroSelectError('cannot select 0 coins')
        for utxo in utxo_list:
            ssum += SimpleColorValue.sum(utxo.colorvalues)
            selection.append(utxo)
            if ssum >= colorvalue:
                return selection, ssum
        raise InsufficientFundsError('not enough coins: %s requested, %s found'
                                     % (colorvalue, ssum))

    def get_required_fee(self, tx_size):
        """Given a transaction that is of size <tx_size>,
        return the transaction fee in Satoshi that needs to be
        paid out to miners.
        """
        # TODO: this should change to something dependent on tx_size
        return SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)


class RawTxSpec(object):
    """Represents a transaction which can be serialized.
    """
    def __init__(self, model, pycoin_tx, composed_tx_spec=None):
        self.model = model
        self.pycoin_tx = pycoin_tx
        self.composed_tx_spec = composed_tx_spec
        self.update_tx_data()

    def get_hex_txhash(self):
        the_hash = self.pycoin_tx.hash()
        return the_hash[::-1].encode('hex')

    def update_tx_data(self):
        """Updates serialized form of transaction.
        """
        s = io.BytesIO()
        self.pycoin_tx.stream(s)
        self.tx_data = s.getvalue()

    @classmethod
    def from_composed_tx_spec(cls, model, composed_tx_spec):
        testnet = model.is_testnet()
        tx = pycoin_txcons.construct_standard_tx(composed_tx_spec, testnet)
        return cls(model, tx, composed_tx_spec)

    @classmethod
    def from_tx_data(cls, model, tx_data):
        pycoin_tx = pycoin_txcons.deserialize(tx_data)
        composed_tx_spec = pycoin_txcons.reconstruct_composed_tx_spec(
            model, pycoin_tx)
        return cls(model, pycoin_tx, composed_tx_spec)

    def sign(self, utxo_list):
        pycoin_txcons.sign_tx(
            self.pycoin_tx, utxo_list, self.model.is_testnet())
        self.update_tx_data()

    def get_tx_data(self):
        """Returns the signed transaction data.
        """
        return self.tx_data

    def get_hex_tx_data(self):
        """Returns the hex version of the signed transaction data.
        """
        return hexlify(self.tx_data).decode("utf8")


def compose_uncolored_tx(tx_spec):
    """ compose a simple bitcoin transaction """
    targets = tx_spec.get_targets()
    ttotal = ColorTarget.sum(targets)
    fee = tx_spec.get_required_fee(500)
    sel_utxos, sum_sel_coins = tx_spec.select_coins(ttotal + fee)
    change = sum_sel_coins - ttotal - fee
    txouts = [ComposedTxSpec.TxOut(target.get_satoshi(), target.get_address())
              for target in targets]
    # give ourselves the change
    if change > 0:
        change_addr = tx_spec.get_change_addr(UNCOLORED_MARKER)
        txouts.append(
            ComposedTxSpec.TxOut(change.get_satoshi(), change_addr))
    return ComposedTxSpec(sel_utxos, txouts)


class TransactionSpecTransformer(object):
    """An object that can transform one type of transaction into another.
    Essentially has the ability to take a transaction, compose it
    and sign it by returning the appropriate objects.

    The general flow of transaction types is this:
    BasicTxSpec -> SimpleOperationalTxSpec -> ComposedTxSpec -> SignedTxSpec
    "basic"     -> "operational"           -> "composed"     -> "signed"
    """

    def __init__(self, model, config):
        """Create a transaction transformer object for wallet_model <model>
        and a wallet configuration <config>
        """
        self.model = model
        self.testnet = config.get('testnet', False)

    def get_tx_composer(self, op_tx_spec):
        """Returns a function which is able to convert a given operational
        tx spec <op_tx_spec> into a composed tx spec
        """
        if op_tx_spec.is_monocolor():
            color_def = op_tx_spec.get_targets()[0].get_colordef()
            if color_def == UNCOLORED_MARKER:
                return compose_uncolored_tx
            else:
                return color_def.compose_tx_spec
        else:
            # TODO: explicit support for OBC only, generalize!
            obc_color_def = None
            for target in op_tx_spec.get_targets():
                color_def = target.get_colordef()
                if color_def is UNCOLORED_MARKER:
                    continue
                if isinstance(color_def, OBColorDefinition):
                    obc_color_def = color_def
                else:
                    obc_color_def = None
                    break
            if obc_color_def:
                return obc_color_def.compose_tx_spec
            else:
                return None

    def classify_tx_spec(self, tx_spec):
        """For a transaction <tx_spec>, returns a string that represents
        the type of transaction (basic, operational, composed, signed)
        that it is.
        """
        if isinstance(tx_spec, BasicTxSpec):
            return 'basic'
        elif isinstance(tx_spec, OperationalTxSpec):
            return 'operational'
        elif isinstance(tx_spec, ComposedTxSpec):
            return 'composed'
        elif isinstance(tx_spec, RawTxSpec):
            return 'signed'
        else:
            return None

    def transform_basic(self, tx_spec, target_spec_kind):
        """Takes a basic transaction <tx_spec> and returns a transaction
        of type <target_spec_kind> which is one of (operational,
        composed, signed).
        """
        if target_spec_kind in ['operational', 'composed', 'signed']:
            if tx_spec.is_monocolor():
                asset = tx_spec.targets[0].get_asset()
                operational_ts = tx_spec.make_operational_tx_spec(asset)
                return self.transform(operational_ts, target_spec_kind)
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform_operational(self, tx_spec, target_spec_kind):
        """Takes an operational transaction <tx_spec> and returns a
        transaction of type <target_spec_kind> which is one of
        (composed, signed).
        """
        if target_spec_kind in ['composed', 'signed']:
            composer = self.get_tx_composer(tx_spec)
            if composer:
                composed = composer(tx_spec)
                return self.transform(composed, target_spec_kind)
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform_composed(self, tx_spec, target_spec_kind):
        """Takes a SimpleComposedTxSpec <tx_spec> and returns
        a signed transaction. For now, <target_spec_kind> must
        equal "signed" or will throw an exception.
        """
        if target_spec_kind in ['signed']:
            rtxs = RawTxSpec.from_composed_tx_spec(self.model, tx_spec)
            rtxs.sign(tx_spec.get_txins())
            return rtxs
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform_signed(self, tx_spec, target_spec_kind):
        """This method is not yet implemented.
        """
        raise InvalidTransformationError('do not know how to transform tx spec')

    def transform(self, tx_spec, target_spec_kind):
        """Transform a transaction <tx_spec> into another type
        of transaction defined by <target_spec_kind> and returns it.
        """
        spec_kind = self.classify_tx_spec(tx_spec)
        if spec_kind is None:
            raise InvalidTransformationError('spec kind is not recognized')
        if spec_kind == target_spec_kind:
            return tx_spec
        if spec_kind == 'basic':
            return self.transform_basic(tx_spec, target_spec_kind)
        elif spec_kind == 'operational':
            return self.transform_operational(tx_spec, target_spec_kind)
        elif spec_kind == 'composed':
            return self.transform_composed(tx_spec, target_spec_kind)
        elif spec_kind == 'signed':
            return self.transform_signed(tx_spec, target_spec_kind)

