Next-gen colored coin client base
=========

The [NGCCC](https://github.com/bitcoinx/ngcccbase) project is a colored coin client written from scratch in Python. Previous attempts involved writing in colored coin concepts into existing clients. This project grew out of those efforts as it was clear that making a new client written from scratch would be more flexible, easier to change and have lower overhead.

Overview of colored coins
------------

Colored coins is a concept which allows the exchange of assets over the internet through the use of the bitcoin blockchain. Each bitcoin unit (aka "Satoshi") can be "colored" by the use of a protocol for issuing, sending and receiving such coins. This can be useful for securities like stocks and bonds as ownership of such securities can be associated with a particular color. The convenience of bitcoin transactions are then brought to these securities while maintaining their own separate chain of ownership apart from bitcoins.

The original white paper is [here](https://bitcoil.co.il/BitcoinX.pdf). A more accessible introduction can be found [here](http://coloredcoins.org/).

To date, there have been several working implementations of this concept, but they were all proofs-of-concept. We are seeking here to implement a client that can actually be used by real users for the issuance of securities and other applications.

Goals
-----------

The goals of this project are as follows:

* Create a flexible and versatile client that can be extended and modified.
* Allow for a stand-alone configuration.
* Allow for optimizations through use of other bitcoin servers.
* Be safe, stable and secure
* Have high performance with relatively little overhead.

Components
------------

* Colored Coin Store (coloredcoinlib) - Stores colored transaction outputs
* Transaction Parsing (utxodb/txcons/blockchain/electrum) - Grab and parse unspent transaction outputs
* JSON-RPC API (ngccc-server/rpc_interface) - Expose functions via JSON-RPC
* Command-line (ngccc/console_interface) - Expose functions via command-line
* Wallet (pwallet/wallet_interface/wallet_model) - Maintain public/private addresses and sign transactions
* Graphical UI (ngccc-gui/ui) - Expose functions via QT GUI.
* Person-to-person trade (p2ptrade) - Allow users to trade assets directly.

Dependencies
------------

These dependencies must be installed on your machine for the QT client:

* [PyQt4](http://pyqt.sourceforge.net/Docs/PyQt4/installation.html) is used to make the GUI.
* [SIP](http://pyqt.sourceforge.net/Docs/sip4/installation.html) is a dependency for PyQT4.

The two can be installed by running `sudo apt-get install python-qt4 python-sip` on a linux machine.


These dependencies are automatically retrieved by setup.py.

* [pycoin](https://github.com/richardkiss/pycoin)  is used to work with transactions. (Particularly, sign them.)
* [python-bitcoinlib](https://github.com/petertodd/python-bitcoinlib) is used to connect to local bitcoind.
* [python-jsonrpc](https://github.com/gerold-penz/python-jsonrpc) is used to create a JSON-RPC API server.
* [bunch](http://github.com/dsc/bunch) is used by python-jsonrpc

Development
------------

Assumptions

 * The following instructions assume you are using a `sh`-like shell like bash.
 * The following instructions assume the environment variable `YOUR_PROJECT_DIRECTORY` contains the path to a directory where you will keep your projects
 * The following instructions assume that the path `"$YOUR_PROJECT_DIRECTORY/env"` exists and is a directory

Instructions

 * Install bitcoind ex. `sudo apt-get install bitcoind` (or use whatever package manager for your linux distro)

 * Create a python virtualenv to work in ex. `cd $YOUR_PROJECT_DIRECTORY/env/ && virtualenv ngcccbase`
 * Activate the virtualenv ex. `source $YOUR_PROJECT_DIRECTORY/env/ngcccbase/bin/activate`
 * Change to your project directory ex. `cd $YOUR_PROJECT_DIRECTORY`
 * Clone ngcccbase ex. `git clone https://github.com/bitcoinx/ngcccbase.git`
 * Change into your cloned copy of ngcccbase ex. `cd $YOUR_PROJECT_DIRECTORY/ngcccbase`
 * Install ngcccbase for development ex. `&& python setup.py develop`

If you want to play with the QT client there are two more steps:

 * Install PyQt4 and SIP ex. `sudo apt-get install python-qt4 python-sip` (or use whatever package manager for your linux distro).
 * Copy PyQT4 and sip to your virtualenv. On ubuntu/debian:

    `cp /usr/lib/python2.7/dist-packages/PyQt4 $YOUR_PROJECT_DIRECTORY/env/ngcccbase/lib/python2.7/site-packages`

    `cp /usr/lib/python2.7/dist-packages/sip* $YOUR_PROJECT_DIRECTORY/env/ngcccbase/lib/python2.7/site-packages`

    `mkdir $YOUR_PROJECT_DIRECTORY/env/ngcccbase/share`

    `mkdir $YOUR_PROJECT_DIRECTORY/env/ngcccbase/share/pyshared`

    `cp -r /usr/share/pyshared/PyQt4 $YOUR_PROJECT_DIRECTORY/env/ngcccbase/share/pyshared`

Mac notes
---------

Instead of bitcoind you can use Bitcoin-Qt in server mode.

   ` cd /Applications/Bitcoin-Qt.app/Contents/MacOS`

   `./Bitcoin-Qt -server -testnet -txindex`

You need to configure a bitcoin.conf with rpcuser and rpcpassword in
`~/Library/Application Support/Bitcoin/`

An easy way to install a python, PyQt4 and sip is with homebrew, `brew install python pyqt`

Make sure to install the pycoin library through github.

`git clone https://github.com/richardkiss/pycoin`

`cd path/to/pycoin`

`sudo make install` 

Testnet Example
---------------

 * `bitcoind -testnet -txindex -daemon`
 * `python ngccc.py setval testnet true`
 * `python ngccc.py newaddr bitcoin`

 The output of this last command is your testnet address, which we'll denote here as {address}. You should see {address} when running this command:

 * `python ngccc.py alladdresses bitcoin`

 Send money to this address using a [testnet faucet](http://tpfaucet.appspot.com/) or
using this command if you already have money in your testnet wallet.
 
 * `bitcoind sendtoaddress {address} .1`
 * `python ngccc.py scan`
 * `python ngccc.py balance bitcoin`
 
 Should return 0.1
 
 * `python ngccc.py issue assetName obc 10000 1`

 Should return a large hash.

Contributors
------------

 * Alex "killerstorm" Mizrahi
 * Jimmy Song
 * Thor "Plazmotech" Correia
 * Victor Knyazhin (coloredcoinlib)
 * Daniel "Ademan" Roberts
 * Adrian Porter
 * Manuel Araoz (coloredcoinlib)

License
-------

MIT (see LICENSE file)

Donations
---------

To financially support this project you can donate to this Bitcoin address: 1uEfNJF2Diz9ADQ3sQ16JyZpZ6qMPKxRk

Sponsors
--------

A big thank you to the following sponsors of this project. They can be seen at the colored coins [home page](http://coloredcoins.org).
