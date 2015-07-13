#!/usr/bin/env python
import sys
import json
import argparse
from ngcccbase.api import Ngccc

parser = argparse.ArgumentParser(description='Chromawallet JSON-RPC server')
parser.add_argument('--config_path', default='config.json')
parser.add_argument('start_server')

args = parser.parse_args()

if __name__ == "__main__":
    with open(args.config_path, 'r') as fo:
        config = json.load(fo)
        api = Ngccc(wallet=config["wallet_path"], testnet=config["testnet"])
        api.bootstrap()
        api.startserver(hostname=config["hostname"], port=config["port"])
