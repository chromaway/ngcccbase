"""
UTXO Fetcher:

fetches information about unspent transaction outputs from
external source (according to config) and feeds it to 
CoinManager.
"""

from ngcccbase.services.blockchain import BlockchainInfoInterface, AbeInterface
from ngcccbase.services.electrum import ElectrumInterface

DEFAULT_ELECTRUM_SERVER = "btc.it-zone.org"
DEFAULT_ELECTRUM_PORT = 50001

class UTXOFetcher(object):
    """Object which can fetch UTXO's. The main sources are:
    blockchain - blockchain.info can provide utxos through JSON
    testnet    - an open-source block explorer using JSON
    electrum   - stratum-protocol servers
    """
    def __init__(self, model, config):
        """Create a fetcher object given configuration in <params>
        """
        self.model = model
        self.coin_manager = model.get_coin_manager()
        params = config.get('utxo_fetcher', {})
        if model.testnet:
            use = 'testnet'
        else:
            use = params.get('interface', 'blockchain.info')
        if use == 'blockchain.info':
            self.interface = BlockchainInfoInterface(self.coin_manager)
        elif use == 'testnet':
            self.interface = AbeInterface()
        elif use == 'electrum':
            electrum_server = params.get(
                'electrum_server', DEFAULT_ELECTRUM_SERVER)
            electrum_port = params.get(
                'electrum_port', DEFAULT_ELECTRUM_PORT)
            self.interface = ElectrumInterface(electrum_server, electrum_port)
        else:
            raise Exception('unknown service for UTXOFetcher')

    def add_utxo(self, address, data):
        self.coin_manager.apply_tx(data[0])
        #self.coin_manager.add_coin(address, *data)

    def scan_address(self, address):
        try:
            for data in self.interface.get_utxo(address):
                self.add_utxo(address, data)
        except Exception as e:
            if "%s" % e != "No JSON object could be decoded":
                print e
                raise

    def scan_all_addresses(self):
        wam = self.model.get_address_manager()
        for address_rec in wam.get_all_addresses():
            self.scan_address(address_rec.get_address())
           
        
