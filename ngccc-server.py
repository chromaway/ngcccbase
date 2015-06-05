#!/usr/bin/env python


import sys
import json
from ngcccbase.api import Ngccc


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: %s <config_path>" % sys.argv[0]
    else:
        with open(sys.argv[1], 'r') as fo:
            config = json.load(fo)
            api = Ngccc(wallet=config["wallet"], testnet=config["testnet"])
            api.startserver(hostname=config["hostname"], port=config["port"])
