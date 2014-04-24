#!/usr/bin/env python

"""
ngccc-server.py

JSON-RPC interface to the Next-Generation Colored Coin Client
This command will start a server at hostname/port that takes
in JSON-RPC commands for execution.
"""

import install_https
from ngcccbase.rpc_interface import RPCRequestHandler
from BaseHTTPServer import HTTPServer
import sys
import getopt

from ngcccbase.logger import setup_logging

setup_logging()

args = []

# grab the hostname and port from the command-line
try:
    opts, args = getopt.getopt(sys.argv[1:], "", "")
except getopt.GetoptError:
    pass

if len(args) != 2:
    print ("Error: parameters are required")
    print ("python ngccc-server.py hostname port")
    sys.exit(2)

hostname = args[0]
port = int(args[1])

# create a server to accept the JSON-RPC requests
http_server = HTTPServer(
    server_address=(hostname, port), RequestHandlerClass=RPCRequestHandler
)

# start the server
print ("Starting HTTP server on http://%s:%s" % (hostname, port))
http_server.serve_forever()
