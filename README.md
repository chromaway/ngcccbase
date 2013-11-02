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

Development
------------

 * Create a python virtualenv to work in
 ex. `cd $YOUR_PROJECT_DIRECTORY/env/ && virtualenv ngcccbase`
 * Activate the virtualenv
 ex. `source $YOUR_PROJECT_DIRECTORY/env/ngcccbase/bin/activate`
 * Clone ngcccbase
 ex. `cd $YOUR_PROJECT_DIRECTORY && git clone https://github.com/bitcoinx/ngcccbase.git`
 * Install ngcccbase for development
 ex `cd $YOUR_PROJECT_DIRECTORY/ngcccbase && python setup.py develop`

Contributors
------------

 * Alex "killerstorm" Mizrahi
 * Jimmy Song
 * Thor "Plazmotech" Correia
 * Victor Knyazhin (coloredcoinlib)
 * Daniel "Ademan" Roberts

License
-------

MIT (see LICENSE file)
