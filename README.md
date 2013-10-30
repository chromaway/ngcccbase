Next-gen colored coin client base
=========

A flexible and modular base for colored coin software.

Includes a basic wallet with command-line interface.

coloredcoinlib handles 'coloring' (color kernels, colorvalues, things like that), while ngcccbase implements wallet model.

Dependencies
------------

(included) [pycoin](https://github.com/richardkiss/pycoin)  is used to work with transactions. (Particularly, sign them.)

(included) [python-bitcoinrpc](https://github.com/jgarzik/python-bitcoinlib) is used to connect to local bitcoind.

(not included) [python-jsonrpc](https://github.com/gerold-penz/python-jsonrpc) is used to create a JSON-RPC API server.

(not included) [bunch](http://github.com/dsc/bunch) is used by python-jsonrpc

Contributors
------------

 * Alex "killerstorm" Mizrahi
 * Jimmy Song
 * Thor "Plazmotech" Correia
 * Victor Knyazhin (coloredcoinlib)

License
-------

MIT (see LICENSE file)
