from bitcoinrpc import authproxy

class COutpoint(object):
    def __init__(self, hash, n):
        self.hash = hash
        self.n = n

class CTxIn(object):
    def __init__(self, op_hash, op_n):
        self.outpoint = COutpoint(op_hash, op_n)

class CTxOut(object):
    def __init__(self, value):
        self.value = value

class CTransaction(object):

    def __init__(self, bs):
        self.bs = bs
        self.have_input_values = False

    @classmethod
    def from_jsonrpc(klass, d, bs):
        tx = CTransaction(bs)

        tx.hash = d['txid']
        tx.inputs = []
        for i in d['vin']:
            if 'coinbase' in i:
                tx.inputs.append(CTxIn('coinbase', 0))
            else:
                tx.inputs.append(CTxIn(i['txid'], i['vout']))
        tx.outputs = []
        for o in d['vout']:
            tx.outputs.append(CTxOut(long(o['value'] * 100000000)))
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
                inp.value = 0 # TODO: value of coinbase tx?
        

class BlockchainState(object):
    def __init__(self, url):
        self.bitcoind = authproxy.AuthServiceProxy(url)
        self.cur_height = None
    
    def get_tx(self, txhash):
        return CTransaction.from_jsonrpc(self.bitcoind.getrawtransaction(txhash, 1), self)

    def iter_block_txs(self, height):
        if (not self.cur_height) or (self.cur_height < height):
            raise Exception("iter_block_txs: height exceeds available height")
        txhashes = self.bitcoind.getblock(self.bitcoind.getblockhash(height))['tx']
        for txhash in txhashes:
            yield self.get_tx(txhash)

    def get_height(self):
        return self.cur_height
    def update(self):
        """make sure we use latest data"""
        self.cur_height = self.bitcoind.getblockcount() - 1


