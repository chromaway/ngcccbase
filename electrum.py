#!/usr/bin/env python

from bitcoin.core import CBitcoinAddress, CTransaction
from bitcoin.core import x as to_binary
from bitcoin.core import b2lx as to_little_endian_hex
from bitcoin.core import b2x as to_hex

import json
import socket
import sys
import time
import traceback


class ElectrumInterface(object):

    def __init__(self, host, port, debug=False):
        self.message_counter = 0
        self.connection = (host, port)
        self.debug = debug
        self.is_connected = False
        self.connect()

    def connect(self):
        "Connects to an electrum server via TCP"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        try:
            sock.connect(self.connection)
        except:
            print "failed to connect to %s:%s" % self.connection
            return

        sock.settimeout(60)
        self.sock = sock
        self.is_connected = True
        if self.debug:
            print "connected to %s:%s" % self.connection
        return True

    def wait_for_response(self, target_id):
        try:
            out = ''
            while self.is_connected or self.connect():
                try:
                    msg = self.sock.recv(1024)
                    if self.debug:
                        print msg
                except socket.timeout:
                    print "socket timed out"
                    self.is_connected = False
                    continue
                except socket.error:
                    traceback.print_exc(file=sys.stdout)
                    raise

                out += msg
                if msg == '':
                    self.is_connected = False

                # get the list of messages by splitting on newline
                raw_messages = out.split("\n")
                out = raw_messages.pop() # the last one isn't complete
                for raw_message in raw_messages:
                    message = json.loads(raw_message)

                    id = message.get('id')
                    error = message.get('error')
                    result = message.get('result')

                    if id == target_id:
                        if error:
                            print "received error %s" % message
                        else:
                            return result
                    else:
                        # just print it for now
                        print message
        except:
            traceback.print_exc(file=sys.stdout)

        self.is_connected = False

    def get_response(self, method, params):
        """return the string response of the message sent to electrum"""
        current_id = self.message_counter
        self.message_counter += 1
        try:
            self.sock.send(
                json.dumps({
                    'id': current_id,
                    'method': method,
                    'params': params})
                + "\n")
        except socket.error:
            traceback.print_exc(file=sys.stdout)
            return None
        return self.wait_for_response(current_id)

    def get_version(self):
        return self.get_response('server.version', ["1.9", "0.6"])

    def get_raw_transaction(self, tx_id, height):
        return self.get_response('blockchain.transaction.get',[tx_id, height])

    def get_utxo(self, address):
        script_pubkey = CBitcoinAddress(address).to_scriptPubKey()
        txs = self.get_response('blockchain.address.get_history',[address])
        spent = {}
        utxos = []
        for tx in txs:
            raw = self.get_raw_transaction(tx['tx_hash'], tx['height'])
            data = CTransaction.deserialize(to_binary(raw))
            for vin in data.vin:
                spent[(to_little_endian_hex(vin.prevout.hash), vin.prevout.n)] = 1
            for outindex, vout in enumerate(data.vout):
                if vout.scriptPubKey == script_pubkey:
                    utxos += [(tx['tx_hash'], outindex, vout.nValue,
                               to_hex(vout.scriptPubKey))]
        return [u for u in utxos if not u[0:2] in spent]

if __name__ == "__main__":
    ei = ElectrumInterface("btc.it-zone.org", 50001)
    print ei.get_utxo("1PAMLeDxXK3DJ4nm6okVHmjH7pmsbg8NYr")

