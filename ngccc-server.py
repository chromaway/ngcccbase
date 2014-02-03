#!/usr/bin/env python

"""
ngccc-server.py

JSON-RPC interface to the Next-Generation Colored Coin Client
This command will start a server at hostname/port that takes
in JSON-RPC commands for execution.
"""

from ngcccbase.rpc_interface import RPCRequestHandler
from BaseHTTPServer import HTTPServer
import sys
import getopt


# grab the hostname and port from the command-line
try:
    opts, args = getopt.getopt(sys.argv[1:], "", "")
except getopt.GetoptError:
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
