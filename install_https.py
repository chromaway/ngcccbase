#!/usr/bin/env python
import urllib2
import httplib
import ssl
import socket
import os
import sys

try:
    main_file = os.path.abspath(sys.modules['__main__'].__file__)
except AttributeError:
    main_file = sys.executable
CERT_FILE = os.path.join(os.path.dirname(main_file), 'cacert.pem')


class ValidHTTPSConnection(httplib.HTTPConnection):
        "This class allows communication via SSL."

        default_port = httplib.HTTPS_PORT

        def __init__(self, *args, **kwargs):
            httplib.HTTPConnection.__init__(self, *args, **kwargs)

        def connect(self):
            "Connect to a host on a given (SSL) port."

            sock = socket.create_connection((self.host, self.port),
                                            self.timeout, self.source_address)
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()
            self.sock = ssl.wrap_socket(sock,
                                        ca_certs=CERT_FILE,
                                        cert_reqs=ssl.CERT_REQUIRED)


class ValidHTTPSHandler(urllib2.HTTPSHandler):

    def https_open(self, req):
            return self.do_open(ValidHTTPSConnection, req)

urllib2.install_opener(urllib2.build_opener(ValidHTTPSHandler))

if __name__ == "__main__": 
        def test_access(url):
                print "Acessing", url
                page = urllib2.urlopen(url)
                print page.info()
                data = page.read()
                print "First 100 bytes:", data[0:100]
                print "Done accesing", url
                print ""

        # This should work
        test_access("https://blockchain.info")
        test_access("http://www.google.com")
        # Accessing a page with a self signed certificate should not work
        # At the time of writing, the following page uses a self signed certificate
        test_access("https://tidia.ita.br/")
