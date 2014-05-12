import unittest
import os, tempfile, shutil

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.services.chroma import ChromaBlockchainState
from ngcccbase.blockchain import VerifierBlockchainState


class TestVerifierBlockchainState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.mkdtemp()
        cls.pwallet = PersistentWallet(os.path.join(cls.tempdir, 'testnet.wallet'), True)
        cls.pwallet.init_model()
        cls.vbs = VerifierBlockchainState(
            cls.pwallet.get_model().store_conn, ChromaBlockchainState())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir)

    def test_(self):
        pass
        self.vbs.start()


if __name__ == '__main__':
    unittest.main()
