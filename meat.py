import ecdsa
import hashlib
import json

sha256 = lambda h: hashlib.sha256(h).digest()
ripemd160 = lambda h: hashlib.new("ripemd160", h).digest()
md5 = lambda h: hashlib.md5(h).digest()

class Address():
	def __init__(self, pubkey, privkey, rawPubkey, rawPrivkey):
		self.pubkey = pubkey
		self.privkey = privkey
		self.rawPrivkey = rawPrivkey
		self.rawPubkey = rawPubkey

	@classmethod
	def new(self):
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

		return self(pubkey, privkey, rawPubkey, rawPrivkey)

	@classmethod
	def fromObj(self, data):
		pubkey = data["pubkey"]
		privkey = data["privkey"]
		rawPubkey = data["rawPubkey"].decode("hex")
		rawPrivkey = data["rawPrivkey"].decode("hex")

		return self(pubkey, privkey, rawPubkey, rawPrivkey)

	def getJSONData(self):
		return {"pubkey":self.pubkey, "privkey":self.privkey, "rawPrivkey":self.rawPrivkey.encode("hex"), "rawPubkey":self.rawPubkey.encode("hex")}
