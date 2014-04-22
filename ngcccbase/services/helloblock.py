import urllib2
import json


class HelloBlockInterface(object):
    def __init__(self, testnet):
        self.net_prefix = "testnet" if testnet else "mainnet"

    def get_tx_confirmations(self, txhash):
        url = "https://%s.helloblock.io/v1/transactions/%s" % \
            (self.net_prefix, txhash)
        try:
            resp = json.loads(urllib2.urlopen(url).read())
            if resp['status'] == 'success':
                return resp['data']['transaction']['confirmations']
        except:
            raise
        return 0

    def get_utxo(self, address):
        url = "https://%s.helloblock.io/v1/addresses/unspents?addresses=%s" % \
            (self.net_prefix, address)
        try:
            resp = json.loads(urllib2.urlopen(url).read())
            if resp['status'] == 'success':
                unspents = resp['data']['unspents']
                utxos = []
                for utxo_data in unspents:
                    utxos.append([utxo_data['txHash'],
                                  utxo_data['index'],
                                  utxo_data['value'],
                                  utxo_data['scriptPubKey']])
                return utxos
        except:
            raise
        return []

    def get_address_history(self, address):
        url = "https://%s.helloblock.io/v1/addresses/%s/transactions?limit=10000" % \
            (self.net_prefix, address)
        resp = json.loads(urllib2.urlopen(url).read())
        if resp['status'] == 'success':
            txs = resp['data']['transactions']
            return [tx['txHash'] for tx in txs]
        raise Exception('error when retrieving history for an address')
