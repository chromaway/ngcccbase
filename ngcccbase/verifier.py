# Library for Simple Payment Verification

from pycoin.encoding import double_sha256


def hash_decode(x):
    return x.decode('hex')[::-1]


def hash_encode(x):
    return x[::-1].encode('hex')


class Verifier(object):
    """Class that Verifies Transactions"""

    def __init__(self, blockchain_state):
        """Create a verifier given a blockchain lookup blockchain_state
        """
        self.blockchain_state = blockchain_state
        self.verified_tx = {}

    def get_confirmations(self, txhash):
        """Returns the number of confirmations of the transaction identified
        by txhash. Returns None if the tx is unknown to the verifier.
        """
        if txhash in self.verified_tx:
            height, timestamp, pos = self.verified_tx[txhash]
            return self.blockchain_state.get_height() - height + 1
        else:
            return None

    def get_merkle_root(self, merkle_s, start_hash, pos):
        """Given a merkle hash list merkle_s and the starting point start_hash
        Hash all the way to the root and get the merkle_root.
        """
        h = hash_decode(start_hash)
        # i is the "level" or depth of the binary merkle tree.
        # item is the complementary hash on the merkle tree at this level
        for i, item in enumerate(merkle_s):
            # figure out if it's the left item or right item at this level
            if pos >> i & 1:
                # right item (odd at this level)
                h = double_sha256(hash_decode(item) + h)
            else:
                # left item (even at this level)
                h = double_sha256(h + hash_decode(item))
        return hash_encode(h)

    def verify_merkle(self, txhash):
        result = self.blockchain_state.get_merkle(txhash)
        merkle, tx_height, pos = result.get('merkle'), \
            result.get('block_height'), result.get('pos')

        # calculate the merkle root and see if it's what the blockchain
        #  says it is
        merkle_root = self.get_merkle_root(merkle, txhash, pos)
        header = self.blockchain_state.get_header(tx_height)
        if not header:
            return False
        if header.get('merkle_root') != merkle_root:
            return False

        timestamp = header.get('timestamp')
        self.verified_tx[txhash] = (tx_height, timestamp, pos)
        return True
