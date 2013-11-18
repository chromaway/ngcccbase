
import urllib2
import json


def get_spends(tx, blockchain_state):
    """ Returns transactions which spend outputs from a given transaction """

    response = urllib2.urlopen('http://explorer.tumak.cz/spends/'+tx)
    j = json.load(response)
    ret = []
    for i, tx_hash, output_n in j:
        ret.append(
            {'txhash': tx_hash,
             'outindex': output_n,
             'blockhash': blockchain_state.get_tx_blockhash(tx_hash)[0]})
    return ret
