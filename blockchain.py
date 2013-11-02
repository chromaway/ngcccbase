
import urllib2
import json

class BlockchainInterface(object):

    @classmethod
    def get_utxo(cls, address):
        url = "http://blockchain.info/unspent?active=%s" % address
        try:
            jsonData = urllib2.urlopen(url).read()
            data = json.loads(jsonData)
            utxos = []
            for utxo_data in data['unspent_outputs']:
                txhash = utxo_data['tx_hash'].decode('hex')[::-1].encode('hex')
                utxo = [txhash, utxo_data['tx_output_n'], utxo_data['value'], utxo_data['script']]
                utxos.append(utxo)
            return utxos
        except urllib2.HTTPError as e:
            if e.code == 500:
                return []
            raise
