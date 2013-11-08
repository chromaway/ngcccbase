#!/usr/bin/env python

from bitcoin.core import CBitcoinAddress, CTransaction
from bitcoin.core import x as to_binary
from bitcoin.core import b2lx as to_little_endian_hex
from bitcoin.core import b2x as to_hex
from coloredcoinlib import blockchain

import json
import socket
import sys
import time
import traceback
import urllib2
import bitcoin.rpc


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
            raise Exception("Unable to connect to %s:%s" % self.connection)

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

                # the last one isn't complete
                out = raw_messages.pop()
                for raw_message in raw_messages:
                    message = json.loads(raw_message)

                    id = message.get('id')
                    error = message.get('error')
                    result = message.get('result')

                    if id == target_id:
                        if error:
                            raise Exception("received error %s" % message)
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
        return self.get_response('blockchain.transaction.get', [tx_id, height])

    def get_utxo(self, address):
        script_pubkey = CBitcoinAddress(address).to_scriptPubKey()
        txs = self.get_response('blockchain.address.get_history', [address])
        spent = {}
        utxos = []
        for tx in txs:
            print tx
            raw = self.get_raw_transaction(tx['tx_hash'], tx['height'])
            data = CTransaction.deserialize(to_binary(raw))
            for vin in data.vin:
                spent[(to_little_endian_hex(vin.prevout.hash),
                       vin.prevout.n)] = 1
            for outindex, vout in enumerate(data.vout):
                if vout.scriptPubKey == script_pubkey:
                    utxos += [(tx['tx_hash'], outindex, vout.nValue,
                               to_hex(vout.scriptPubKey))]
        return [u for u in utxos if not u[0:2] in spent]


class EnhancedBlockchainState(blockchain.BlockchainState):

    def __init__(self, url, port):
        self.interface = ElectrumInterface(url, port)
        self.bitcoind = bitcoin.rpc.RawProxy()
        self.cur_height = None

    def get_tx_block_height(self, txhash):
        url = "http://blockchain.info/rawtx/%s" % txhash
        jsonData = urllib2.urlopen(url).read()
        if jsonData[0] != '{':
            return (None, False)
        data = json.loads(jsonData)
        return (data.get("block_height", None), True)

    def get_raw_transaction(self, txhash):
        try:
            # try the bitcoind first
            raw = self.bitcoind.getrawtransaction(txhash, 0)
        except:
            try:
                # first, grab the tx height
                height = self.get_tx_block_height(txhash)[0]
                if not height:
                    raise Exception("")

                # grab the transaction from electrum
                raw = self.interface.get_raw_transaction(txhash, height)
            except:
                raise Exception("Could not connect to blockchain and/or"
                                "electrum server to grab the data we need")
        return raw

    def get_tx(self, txhash):
        txhex = self.get_raw_transaction(txhash)
        tx = CTransaction.deserialize(to_binary(txhex))
        return blockchain.CTransaction.from_bitcoincore(txhash, tx, self)


if __name__ == "__main__":
    ei = ElectrumInterface("btc.it-zone.org", 50001)
    print ei.get_utxo("1PAMLeDxXK3DJ4nm6okVHmjH7pmsbg8NYr")
    bcs = EnhancedBlockchainState("btc.it-zone.org", 50001)
    print bcs.get_tx(
        "abcc3e3f6ef2e989f1905f77b4e74326a156b941e803abc4d9175e82180be808")
    print bcs.get_tx_block_height(
        "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16")
