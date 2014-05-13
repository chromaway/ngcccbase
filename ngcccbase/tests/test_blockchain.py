import unittest
import os, tempfile, shutil
import time

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.services.chroma import ChromaBlockchainState
from ngcccbase.blockchain import VerifierBlockchainState


class TestVerifierBlockchainState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        #cls.tempdir = tempfile.mkdtemp()
        cls.tempdir = '/path/to/folder'
        cls.pwallet = PersistentWallet(os.path.join(cls.tempdir, 'testnet.wallet'), True)
        cls.pwallet.init_model()
        cls.vbs = VerifierBlockchainState(cls.tempdir, ChromaBlockchainState())

    @classmethod
    def tearDownClass(cls):
        #shutil.rmtree(cls.tempdir)
        pass

    def test_(self):
        pass
        self.vbs.start()
        while self.vbs.is_running():
            time.sleep(0.1)


if __name__ == '__main__':
    unittest.main()
