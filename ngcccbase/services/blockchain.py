"""
blockchain.py

This is a connector to JSON based URL's such as blockchain.info
For now, the main usage of this file is to grab the utxo's for a
given address.
UTXO's (Unspent Transaction Outputs) are the record of transactions
for an address that haven't been spent yet.
"""
import urllib2
import json


class WebBlockchainInterface(object):
    """Abstract class for processing actual utxo's from a given web
    provider.
    """
    URL_TEMPLATE = None
    REVERSE_TXHASH = False

    @classmethod
    def get_utxo(cls, address):
        """Returns Unspent Transaction Outputs for a given address
        as an array of arrays. Each array in the array is a list of
        four elements that are necessary to initialize a UTXO object
        from utxodb.py
        """
        url = cls.URL_TEMPLATE % address
        try:
            jsonData = urllib2.urlopen(url).read()
            data = json.loads(jsonData)
            utxos = []
            for utxo_data in data['unspent_outputs']:
                txhash = utxo_data['tx_hash']
                if cls.REVERSE_TXHASH:
                    txhash = txhash.decode('hex')[::-1].encode('hex')
                utxo = [txhash, utxo_data['tx_output_n'],
                        utxo_data['value'], utxo_data['script']]
                utxos.append(utxo)
            return utxos
        except urllib2.HTTPError as e:
            if e.code == 500:         
                return []             
            raise                       # pragma: no cover


class BlockchainInfoInterface(WebBlockchainInterface):
    """Interface for blockchain.info. DO NOT USE FOR TESTNET!
    """
    URL_TEMPLATE = "http://blockchain.info/unspent?active=%s"
    REVERSE_TXHASH = True


class AbeInterface(WebBlockchainInterface):
    """Interface for an Abe server, which is an open-source
    version of block explorer.
    See https://github.com/bitcoin-abe/bitcoin-abe for more information.
    """
    URL_TEMPLATE = "http://abe.bitcontracts.org/unspent/%s"
