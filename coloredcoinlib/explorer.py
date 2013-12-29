
import urllib2
import json

BASE_URL = "http://abe.bitcontracts.org"


def get_spends(tx, blockchain_state):
    """ Returns transactions which spend outputs from a given transaction
    """
    url = '%s/spends/%s' % (BASE_URL, tx)
    response = urllib2.urlopen(url)
    ret = []
    for i, tx_hash, output_n in json.load(response):
        ret.append(
            {'txhash': tx_hash,
             'outindex': output_n,
             'blockhash': blockchain_state.get_tx_blockhash(tx_hash)})
    return ret
