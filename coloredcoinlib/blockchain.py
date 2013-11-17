import bitcoin.core
import bitcoin.serialize
import bitcoin.rpc

class COutpoint(object):
    def __init__(self, hash, n):
        self.hash = hash
        self.n = n


class CTxIn(object):
    def __init__(self, op_hash, op_n):
        self.outpoint = COutpoint(op_hash, op_n)


class CTxOut(object):
    def __init__(self, value, scriptPubKey=None):
        self.value = value
        self.raw_address = None

        # extract the destination address from the scriptPubkey
        if scriptPubKey and scriptPubKey[:3] == "\x76\xa9\x14":
            self.raw_address = scriptPubKey[3:23]


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
            prev_tx_hash = inp.outpoint.hash
            if prev_tx_hash != 'coinbase':
                prevtx = self.bs.get_tx(prev_tx_hash)
                inp.value = prevtx.outputs[inp.outpoint.n].value
            else:
                inp.value = 0  # TODO: value of coinbase tx?


class BlockchainState(object):
    def __init__(self, bitcoind):
        self.bitcoind = bitcoind
        self.cur_height = None

    @classmethod
    def from_url(cls, url, testnet=False):
        if testnet:
            bitcoind = bitcoin.rpc.RawProxy(
                service_url=url, service_port=18332)
        else:
            bitcoind = bitcoin.rpc.RawProxy(service_url=url)
        return cls(bitcoind)

    def get_tx_block_height(self, txhash):
        try:
            raw = self.bitcoind.getrawtransaction(txhash, 1)
        except:
            return (None, False)
        if 'blockhash' in raw:
            block_data = self.bitcoind.getblock(raw['blockhash'])
            return (block_data['height'], False)
        else:
            return (None, True)

    def get_tx(self, txhash):
        txhex = self.bitcoind.getrawtransaction(txhash, 0)
        txbin = bitcoin.core.x(txhex)
        tx = bitcoin.core.CTransaction.deserialize(txbin)
        return CTransaction.from_bitcoincore(txhash, tx, self)

    def iter_block_txs(self, height):
        block_hex = None
        try:
            block_hex = self.bitcoind.getblock(
                self.bitcoind.getblockhash(height), False)
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
            txhashes = self.bitcoind.getblock(
                self.bitcoind.getblockhash(height))['tx']
            for txhash in txhashes:
                yield self.get_tx(txhash)

    def get_height(self):
        return self.cur_height

    def update(self):
        """make sure we use latest data"""
        self.cur_height = self.bitcoind.getblockcount() - 1
