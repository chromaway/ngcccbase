
import urllib2
import json

""" Returns transactions which spend outputs from a given transaction """
def get_spends(tx, blockchain_state):
    response = urllib2.urlopen('http://explorer.tumak.cz/spends/'+tx)
    j = json.load(response)
    ret = []
    for i, tx_hash, output_n in j:
        print i, tx_hash, output_n
        ret.append({'txhash': tx_hash,
               'outindex': output_n,
               'height': blockchain_state.get_tx_block_height(tx_hash)})
    return ret


