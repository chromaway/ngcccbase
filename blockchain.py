
import urllib2
import json

class BlockchainInterface(object):

    URL_TEMPLATE = "http://blockchain.info/unspent?active=%s"

    @classmethod
    def get_utxo(cls, address):
        url = cls.URL_TEMPLATE % address
        try:
            jsonData = urllib2.urlopen(url).read()
            data = json.loads(jsonData)
            utxos = []
            for utxo_data in data['unspent_outputs']:
                utxo = [utxo_data['tx_hash'], utxo_data['tx_output_n'], utxo_data['value'], utxo_data['script']]
                utxos.append(utxo)
            return utxos
        except urllib2.HTTPError as e:
            if e.code == 500:
                return []
            raise

class TestnetInterface(BlockchainInterface):

    URL_TEMPLATE = "http://explorer.tumak.cz/unspent/%s"
    
