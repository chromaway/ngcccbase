#!/usr/bin/env python

"""
ngccc-server.py

JSON-RPC interface to the Next-Generation Colored Coin Client
This command will start a server at hostname/port that takes
in JSON-RPC commands for execution.
"""

import argparse
from BaseHTTPServer import HTTPServer
from ngcccbase.rpc_interface import RPCRequestHandler

def get_arguments():
  parser = argparse.ArgumentParser()
  parser.add_argument("--hostname", default="localhost", 
                      help="default: localhost")
  parser.add_argument("--port", type=int, default=8080, 
                      help="default: 8080")
  parser.add_argument("--wallet",  
                      help="default: <blockchain>.wallet")
  parser.add_argument("--testnet", action="store_true",
                      help="use testnet blockchain")
  args = vars(parser.parse_args())
  args["blockchain"] = "testnet" if args["testnet"] else "mainnet"
  if not args["wallet"]:
    args["wallet"] = "%s.wallet" % args["blockchain"]
  return args

if __name__ == "__main__":
  args = get_arguments()
  print """Starting json-rpc service
  Location: http://%(hostname)s:%(port)s 
  Blockchain: %(blockchain)s 
  Wallet: %(wallet)s """ % args
  http_server = HTTPServer(
    server_address=(args["hostname"], args["port"]), 
    RequestHandlerClass=RPCRequestHandler
  )
  http_server.args = args
  http_server.serve_forever()

