Next-gen colored coin client base
=========

A flexible and modular base for colored coin software.

Includes a basic wallet with command-line interface.

coloredcoinlib handles 'coloring' (color kernels, colorvalues, things like that), while ngcccbase implements wallet model.

Dependencies
------------

Dependencies are automatically retrieved by setup.py.

* [pycoin](https://github.com/richardkiss/pycoin)  is used to work with transactions. (Particularly, sign them.)

* [python-bitcoinrpc](https://github.com/jgarzik/python-bitcoinlib) is used to connect to local bitcoind.

* [python-jsonrpc](https://github.com/gerold-penz/python-jsonrpc) is used to create a JSON-RPC API server.

* [bunch](http://github.com/dsc/bunch) is used by python-jsonrpc

Development
------------

Assumptions

 * The following instructions assume you are using a `sh`-like shell like bash.

 * The following instructions assume the environment variable `YOUR_PROJECT_DIRECTORY` contains the path to a directory where you will keep your projects

 * The following instructions assume that the path `"$YOUR_PROJECT_DIRECTORY/env"` exists and is a directory

Instructions

 * Create a python virtualenv to work in ex. `cd $YOUR_PROJECT_DIRECTORY/env/ && virtualenv ngcccbase`

 * Activate the virtualenv ex. `source $YOUR_PROJECT_DIRECTORY/env/ngcccbase/bin/activate`

 * Change to your project directory ex. cd `$YOUR_PROJECT_DIRECTORY`

 * Clone ngcccbase ex. `git clone https://github.com/bitcoinx/ngcccbase.git`

 * Change into your cloned copy of ngcccbase ex. `cd $YOUR_PROJECT_DIRECTORY/ngcccbase`

 * Install ngcccbase for development ex `&& python setup.py develop`

Testnet Example
---------------

 * `bitcoind -testnet -txindex -daemon`
 * `python ngccc.py setval testnet true`
 * `python ngccc.py newaddr bitcoin`

 send money to this address
 
 * `bitcoind sendtoaddress mmhmMNfBiZZ37g1tgg2t8DDbNoEdqKVxAL .1`
 
 this is the address returned by the last command, or run `python ngccc.py alladdresses bitcoin` to see the addresses to send testcoins.
 
 * `python ngccc.py scan`
 * `python ngccc.py balance bitcoin`
 
 should say 0.1
 
 * `python ngccc.py issue assetName obc 1 10000`

Contributors
------------

 * Alex "killerstorm" Mizrahi
 * Jimmy Song
 * Thor "Plazmotech" Correia
 * Victor Knyazhin (coloredcoinlib)
 * Daniel "Ademan" Roberts
 * Adrian Porter

License
-------

MIT (see LICENSE file)

Donations
---------

To financially support this project you can donate to this Bitcoin address: 1uEfNJF2Diz9ADQ3sQ16JyZpZ6qMPKxRk
