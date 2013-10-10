Colored Coin Agent (Python)
===========================

The colored coin toolkit. Current version is just a basic demo.

Contributors:

 * Alex Mizrahi <alex.mizrahi@gmail.com>
 * Victor ***

License: GNU AGPL v.3 (see LICENSE)

What
----

To run this demo you need:

 * bitcoind/Bitcoin-Qt with JSON-RPC API, running on testnet, with txindex
   (bitcoind -testnet -txindex -daemon)
 * Jeff Garzic's python-bitcoinrpc library
 * Python 2.x
 * SQLite3 library for Python

Edit test.py to change connection parameters, run `python test.py`, Ctrl-C when bored.
Transactions are stored in color.db
 
