"""
pycoin_txcons.py

Construct and sign transactions using pycoin library
"""

from pycoin.encoding import bitcoin_address_to_hash160_sec,\
    wif_to_tuple_of_secret_exponent_compressed
from pycoin.serialize import b2h, b2h_rev

from pycoin.tx import SecretExponentSolver
from pycoin.tx.Tx import Tx, SIGHASH_ALL
from pycoin.tx.TxIn import TxIn
from pycoin.tx.TxOut import TxOut

from pycoin.tx.script import tools
from pycoin.tx.script.vm import verify_script

from io import BytesIO

from coloredcoinlib import txspec
from coloredcoinlib.blockchain import script_to_raw_address


def construct_standard_tx(composed_tx_spec, is_test):
    txouts = []
    STANDARD_SCRIPT_OUT = "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG"
    for txout in composed_tx_spec.get_txouts():
        hash160 = bitcoin_address_to_hash160_sec(txout.target_addr, is_test)
        script_text = STANDARD_SCRIPT_OUT % b2h(hash160)
        script_bin = tools.compile(script_text)
        txouts.append(TxOut(txout.value, script_bin))
    txins = []
    for cts_txin in composed_tx_spec.get_txins():
        txins.append(TxIn(cts_txin.get_txhash(), cts_txin.prevout.n))
    version = 1
    lock_time = 0
    return Tx(version, txins, txouts, lock_time)


def sign_tx(tx, utxo_list, is_test):
    secret_exponents = [utxo.address_rec.rawPrivKey
                        for utxo in utxo_list if utxo.address_rec]
    solver = SecretExponentSolver(secret_exponents)
    txins = tx.txs_in[:]
    hash_type = SIGHASH_ALL
    for txin_idx in xrange(len(txins)):
        blank_txin = txins[txin_idx]
        utxo = None
        for utxo_candidate in utxo_list:
            if utxo_candidate.get_txhash() == blank_txin.previous_hash \
                    and utxo_candidate.outindex == blank_txin.previous_index:
                utxo = utxo_candidate
                break
        if not (utxo and utxo.address_rec):
            continue
        txout_script = utxo.script.decode('hex')
        signature_hash = tx.signature_hash(
            txout_script, txin_idx, hash_type=hash_type)
        txin_script = solver(txout_script, signature_hash, hash_type)
        txins[txin_idx] = TxIn(blank_txin.previous_hash,
                               blank_txin.previous_index,
                               txin_script)
        if not verify_script(txin_script, txout_script,
                             signature_hash, hash_type=hash_type):
            raise Exception("invalid script")
    tx.txs_in = txins

def deserialize(tx_data):
    return Tx.parse(BytesIO(tx_data))

def reconstruct_composed_tx_spec(model, tx):
    if isinstance(tx, str):
        tx = deserialize(tx)
    if not isinstance(tx, Tx):
        raise Exception('tx is neiether string nor pycoin.tx.Tx')

    pycoin_tx = tx

    txins, txouts = [], []

    for py_txin in pycoin_tx.txs_in:
        # lookup the previous hash and generate the utxo
        in_txhash, in_outindex = py_txin.previous_hash, py_txin.previous_index
        in_txhash = in_txhash[::-1].encode('hex')

        txins.append(txspec.ComposedTxSpec.TxIn(in_txhash, in_outindex))
        # in_tx = ccc.blockchain_state.get_tx(in_txhash)
        # value = in_tx.outputs[in_outindex].value
        # raw_address = script_to_raw_address(py_txin.script)
        # address = ccc.raw_to_address(raw_address)

    for py_txout in pycoin_tx.txs_out:
        script = py_txout.script
        raw_address = script_to_raw_address(script)
        if raw_address:
            address = model.ccc.raw_to_address(raw_address)
        else:
            address = None
        txouts.append(txspec.ComposedTxSpec.TxOut(py_txout.coin_value, address))
    return txspec.ComposedTxSpec(txins, txouts)
