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
        utxo = cts_txin.utxo
        prev_txhash = utxo.txhash.decode('hex')[::-1]
        txins.append(TxIn(prev_txhash, utxo.outindex))
    version = 0
    lock_time = 0
    return Tx(version, txins, txouts, lock_time)
    
def sign_tx(composed_tx_spec, tx, is_test):
    utxos = [txin.utxo for txin in composed_tx_spec.get_txins()]
    secret_exponents = [
        wif_to_tuple_of_secret_exponent_compressed(
            utxo.address_rec.address.privkey, is_test=is_test)[0]
        for utxo in utxos
        if utxo.address_rec]
    solver = SecretExponentSolver(secret_exponents)
    txins = tx.txs_in[:]
    hash_type = SIGHASH_ALL
    for txin_idx in xrange(len(txins)):
        utxo = utxos[txin_idx]
        if utxo.address_rec is None:
            continue
        blank_txin = txins[txin_idx]
        txout_script = utxo.script.decode('hex')
        signature_hash = tx.signature_hash(txout_script, txin_idx, hash_type=hash_type)
        txin_script = solver(txout_script, signature_hash, hash_type)
        txins[txin_idx] = TxIn(blank_txin.previous_hash,
                               blank_txin.previous_index,
                               txin_script)
    tx.txs_in = txins
