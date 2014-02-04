"""
Data structures to model bitcoin blockchain objects.
"""

import bitcoin.core
import bitcoin.serialize
import bitcoin.rpc

from toposort import toposorted


def script_to_raw_address(script):
    # extract the destination address from the scriptPubkey
    if script[:3] == "\x76\xa9\x14":
        return script[3:23]
    else:
        return None


class COutpoint(object):
    def __init__(self, hash, n):
        self.hash = hash
        self.n = n


class CTxIn(object):
    def __init__(self, op_hash, op_n):
        self.prevout = COutpoint(op_hash, op_n)

    def get_txhash(self):
        if self.prevout.hash == 'coinbase':
            return self.prevout.hash
        else:
            return self.prevout.hash.decode('hex')[::-1]

    def get_outpoint(self):
        return (self.prevout.hash, self.prevout.n)


class CTxOut(object):
    def __init__(self, value, script):
        self.value = value
        self.script = script
        self.raw_address = script_to_raw_address(script)


class CTransaction(object):

    def __init__(self, bs):
        self.bs = bs
        self.have_input_values = False

    @classmethod
    def from_bitcoincore(klass, txhash, bctx, bs):
        tx = CTransaction(bs)

        tx.raw = bctx
        tx.hash = txhash
        tx.inputs = []
        for i in bctx.vin:
            if i.prevout.is_null():
                tx.inputs.append(CTxIn('coinbase', 0))
            else:
                op = i.prevout
                tx.inputs.append(CTxIn(bitcoin.core.b2lx(op.hash),
                                       op.n))
        tx.outputs = []
        for o in bctx.vout:
            tx.outputs.append(CTxOut(o.nValue, o.scriptPubKey))
        return tx

    def ensure_input_values(self):
        if self.have_input_values:
            return
        for inp in self.inputs:
            prev_tx_hash = inp.prevout.hash
            if prev_tx_hash != 'coinbase':
                prevtx = self.bs.get_tx(prev_tx_hash)
                inp.value = prevtx.outputs[inp.prevout.n].value
            else:
                inp.value = 0  # TODO: value of coinbase tx?
        self.have_input_values = True


class BlockchainState(object):
    """ Represents a blockchain state, using bitcoin-RPC to
    obtain information of transactions, addresses, and blocks. """
    def __init__(self, bitcoind):
        self.bitcoind = bitcoind

    @classmethod
    def from_url(cls, url, testnet=False):
        if testnet:
            bitcoind = bitcoin.rpc.RawProxy(
                service_url=url, service_port=18332)
        else:
            bitcoind = bitcoin.rpc.RawProxy(  # pragma: no cover
                service_url=url)              # pragma: no cover
        return cls(bitcoind)

    def get_block_height(self, blockhash):
        block = self.bitcoind.getblock(blockhash)
        return block['height']

    def get_blockhash_at_height(self, height):
        return self.bitcoind.getblockhash(height)

    def get_previous_blockinfo(self, blockhash):
        block_data = self.bitcoind.getblock(blockhash)
        return block_data['previousblockhash'], block_data['height']

    def get_tx_blockhash(self, txhash):
        try:
            raw = self.bitcoind.getrawtransaction(txhash, 1)
        except Exception, e:
            # print txhash, e
            return None, False
        return raw.get('blockhash', None), True

    def get_raw(self, txhash):
        return self.bitcoind.getrawtransaction(txhash, 0)

    def get_tx(self, txhash):
        txhex = self.bitcoind.getrawtransaction(txhash, 0)
        txbin = bitcoin.core.x(txhex)
        tx = bitcoin.core.CTransaction.deserialize(txbin)
        return CTransaction.from_bitcoincore(txhash, tx, self)

    def get_best_blockhash(self):
        try:
            return self.bitcoin.getbestblockhash()
        except:
            # warning: not atomic!
            # remove once bitcoin 0.9 becomes commonplace
            count = self.bitcoind.getblockcount()
            return self.bitcoind.getblockhash(count)

    def iter_block_txs(self, blockhash):
        block_hex = None
        try:
            block_hex = self.bitcoind.getblock(blockhash, False)
        except bitcoin.rpc.JSONRPCException:
            pass

        if block_hex:
            # block at once
            block = bitcoin.core.CBlock.deserialize(bitcoin.core.x(block_hex))
            block_hex = None
            for tx in block.vtx:
                txhash = bitcoin.core.b2lx(
                    bitcoin.serialize.Hash(tx.serialize()))
                yield CTransaction.from_bitcoincore(txhash, tx, self)
        else:
            txhashes = self.bitcoind.getblock(blockhash)['tx']
            for txhash in txhashes:
                yield self.get_tx(txhash)

    def sort_txs(self, tx_list):
        block_txs = {h:self.get_tx(h) for h in tx_list}

        def get_dependent_txs(tx):
            """all transactions from current block this transaction
            directly depends on"""
            dependent_txs = []
            for inp in tx.inputs:
                if inp.prevout.hash in block_txs:
                    dependent_txs.append(block_txs[inp.prevout.hash])
            return dependent_txs

        return toposorted(block_txs.values(), get_dependent_txs)

    def get_mempool_txs(self):
        return self.sort_txs(self.bitcoind.getrawmempool())
