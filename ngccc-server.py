#!/usr/bin/python

from rpc_interface import RPCRequestHandler
from BaseHTTPServer import HTTPServer
import json


def main():
    import sys
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "", [])
    except getopt.GetoptError:
        print "arg error"
        sys.exit(2)

    hostname = args[0]
    port = int(args[1])

    http_server = HTTPServer(
        server_address=(hostname, port), RequestHandlerClass=RPCRequestHandler
    )
    print "Starting HTTP server on http://%s:%s" % (hostname, port)
    http_server.serve_forever()

if __name__ == "__main__":
    main()
