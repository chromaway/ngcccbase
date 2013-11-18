
import urllib2
import json

BASE_URL = "http://explorer.tumak.cz"

def get_spends(tx, blockchain_state):
    """ Returns transactions which spend outputs from a given transaction """

    response = urllib2.urlopen(BASE_URL + '/spends/' + tx)
    ret = []
    for i, tx_hash, output_n in json.load(response):
        ret.append(
            {'txhash': tx_hash,
             'outindex': output_n,
             'blockhash': blockchain_state.get_tx_blockhash(tx_hash)[0]})
    return ret
