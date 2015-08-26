#!/usr/bin/env python
import sys
import json
import argparse
from ngcccbase.api import Ngccc
from ngcccbase import testing_config
import logging
from ngcccbase import logger

logger.setup_logging()
logger = logging.getLogger('ngcccbase')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Chromawallet JSON-RPC server')
    parser.add_argument('--config_path', default='config.json')

    args = parser.parse_args()
    with open(args.config_path, 'r') as fo:
        config = json.load(fo)
        testing_config.regtest_server = config.get('regtest_server', None)
        api = Ngccc(wallet=config["wallet_path"], testnet=config["testnet"])
        api.bootstrap()
        api.startserver(hostname=config["hostname"], port=config["port"])
