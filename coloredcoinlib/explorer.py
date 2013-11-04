
import urllib2
import json

""" Returns transactions which spend outputs from a given transaction """
def get_spends(tx):
    response = urllib2.urlopen('http://explorer.tumak.cz/spends/'+tx)
    j = json.load(response)
    ret = []
    for i, tx_hash, output_n in j:
        print i, tx_hash, output_n
        ret.append({'txhash': tx_hash,
               'outindex': output_n,
               'height': 46442}) #TODO: fix height
    return 



if __name__ == "__main__":
    print get_spends("a8d3c4b20b25dab4465f6e2039194a424331a2dcf899c28e8fb811864f64a3a1")