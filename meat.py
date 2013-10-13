import ecdsa
import hashlib
import json
import util
import pycoin.tx
import urllib2

# Lambda's for hashes
sha256 = lambda h: hashlib.sha256(h).digest()
ripemd160 = lambda h: hashlib.new("ripemd160", h).digest()
md5 = lambda h: hashlib.md5(h).digest()

# Address class handles the actual address pairs,
# It creates them from using standard SECP256k1
# We should review the secp256k1 code and make sure it's right for security.

class Address():
    def __init__(self, pubkey, privkey, rawPubkey, rawPrivkey):
        self.pubkey = pubkey
        self.privkey = privkey
        self.rawPrivkey = rawPrivkey
        self.rawPubkey = rawPubkey

    # Creates new pair and returns address object
    @classmethod
    def new(cls):
        # Generates warner ECDSA objects
        ecdsaPrivkey = ecdsa.SigningKey.generate(curve=ecdsa.curves.SECP256k1)
        ecdsaPubkey = ecdsaPrivkey.get_verifying_key()

        rawPrivkey = ecdsaPrivkey.to_string()
        rawPubkey = "\x00" + ripemd160(sha256("\x04" + ecdsaPubkey.to_string()))
        pubkeyChecksum = sha256(sha256(rawPubkey))[:4]
        rawPubkey += pubkeyChecksum

        pubkey = util.b58encode(rawPubkey)
        privkey = "\x80" + rawPrivkey
        privkeyChecksum = sha256(sha256(privkey))[:4]
        privkey = util.b58encode(privkey + privkeyChecksum)

        return cls(pubkey, privkey, rawPubkey, rawPrivkey)

    # Creates pair from JSON parsed into standard python objects and returns address object
    @classmethod
    def fromObj(cls, data):
        pubkey = data["pubkey"]
        privkey = data["privkey"]
        rawPubkey = data["rawPubkey"].decode("hex")
        rawPrivkey = data["rawPrivkey"].decode("hex")

        return cls(pubkey, privkey, rawPubkey, rawPrivkey)

    # Returns JSON parsed into standard python objects and returns dictionary. This is for use with fromObj classmethod.
    def getJSONData(self):
        return {"pubkey":self.pubkey, "privkey":self.privkey, "rawPrivkey":self.rawPrivkey.encode("hex"), "rawPubkey":self.rawPubkey.encode("hex")}

# This class represents an unspent transaction output.
class UTXO(object):
    def __init__(self, txhash, outindex, value, script):
        self.txhash = txhash
        self.outindex = outindex
        self.value = value
        self.script = script

    # I assume this outputs utxo object data as pycoin utxo data for use with pycoin send [verification needed]
    def get_pycoin_coin_source(self):
        le_txhash = self.txhash.decode('hex')[::-1]
        pycoin_txout = pycoin.tx.TxOut(self.value, self.script.decode('hex'))
        return (le_txhash, self.outindex, pycoin_txout)

# Fetches UTXO's for specific address
class UTXOFetcher(object):
    def get_for_address(self, address):
        url = "http://blockchain.info/unspent?active=%s" % address
        try:
            jsonData = urllib2.urlopen(url).read()
            data = json.loads(jsonData)
            utxos = []
            for utxo_data in data['unspent_outputs']:
                txhash = utxo_data['tx_hash'].decode('hex')[::-1].encode('hex')
                utxo = UTXO(txhash, utxo_data['tx_output_n'], utxo_data['value'], utxo_data['script'])
                utxos.append(utxo)
                return utxos
        except urllib2.HTTPError as e:
            if e.code == 500:
                return []
            else:
                raise

# [verification needed]
class TransactionData(object):
    def __init__(self):
        self.unspent = UTXOFetcher()
