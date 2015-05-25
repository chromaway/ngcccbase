import json
import apigen
from ngcccbase import sanitize
from ngcccbase.api import Ngccc as base_api
from ngcccbase.api import AddressNotFound

def parse_config(config_path):
    with open(config_path, 'r') as fo:
            config = json.load(fo)
    return config



class Ngccc(base_api):
    """Next-Generation Colored Coin Client RPC interface. This must start with 
       the startserver command, or it will not initialize properly"""

    def __init__(self):
        pass

    @apigen.command(rpc=False)
    def startserver(self, config_path=None):
        """Starts chromawallet json-rpc service."""

        if config_path is None:
            config_path = './config.json'
            
        config = parse_config(config_path)
        hostname = config['hostname']
        port = sanitize.integer(config['port'])
        testnet = sanitize.flag(config['testnet'])
        wallet_path = config['wallet_path']
        super(Ngccc, self).__init__(wallet=wallet_path, testnet=testnet)
        super(Ngccc, self).startserver(hostname=hostname, port=port, daemon=False)
