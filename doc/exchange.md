Please note that this documentation is a work in progress. [text in square brackets] are placeholders or comments about the development of the documentation, while `<text in angle brackets>` are placeholders for the user's particular setup.

Trying out chromawallet's JSON API
===============

For exchange use and other uses. Note that chromawallet-server is not meant to be run over an untrusted network. Use firewall rules accordingly.

Starting and stopping chromawallet from the command line
---------------
The chromawallet can be run both from the command line and as a background server. For running it from the command line, type:

    ./chromawallet-server startserver

The server will start with configuration parameters found in ```config.json```. If you want to start the server with another config file, add the ```config_path``` switch when starting:

    ./chromawallet-server --config_path=<other_config.json>


Ctrl-c will stop the wallet in the terminal.

The contents of the config file
--------------------

The config.json file looks like this:

    {
        "port": 8080,
        "hostname": "localhost",
        "wallet_path": "test.wallet",
        "testnet": true

    }

port - what port the json-rpc server should listen to

hostname - what interface the server should listen to. "localhost" will only allow connections from a client on localhost. Use e.g. "0.0.0.0" for accepting connections from everywhere. Make sure your computer is properly firewalled for production use.

wallet_path - path to the wallet database. The wallet database is used by the server process. If you specify a path where no file exists, chromawallet-server will create a new wallet for you there.

testnet - controls whether the wallet should be a testnet wallet, that is operate with bitcoin addresses and colored coins on the testnet3 network, or if the wallet should operate on the real bitcoin network, with real bitcoins. The testnet setting must agree with the wallet you specify on wallet_path. A wallet cannot be switched to and from testnet. If you specify a path that creates a new wallet, the wallet will take its testnet setting from the "testnet" setting. So for a live wallet, ```testnet``` should be set to ```false```.

Running chromawallet as a service/daemon
---------------

If you want to run the wallet as a service/daemon, you can use supervisord for this. See:

* [Running chromawallet as a service/daemone](./service-daemon.md)


Running from source
-----------------------------------------

Follow the below two links if you are interested in running the chromawallet-server from source.

* [Running chromawallet from source](./run-from-source.md)
* [Running chromawallet from source as a service/daemon](./source-as-daemon.md)


JSON-RPC clients
---------------------
For these example pyjsonrpc under python 2.7 will be used, but any JSON-RPC client in any language should work , such as node-json-rpc in javascript.

## Error handling

See:
* [Error handling](./error-handling.md)

Testing that the server is up
-----------------------

Whether you are running chromawallet-server from the command line or from supervisord, you can use a json-rpc client to check that the server is up and working.

Example in python with pyjsonrpc:

    import pyjsonrpc

    client = pyjsonrpc.HttpClient(url = "http://localhost:8080")

    client.dumpconfig()

pyjsonrpc can be found at  ( https://pypi.python.org/pypi/python-jsonrpc )

In python, pysjonrpc will automatically convert to and from JSON and python's native data structures (e.g. dictionaries).

Creating an asset
-------------------
In order to create an asset with colored coins, you must let the software make a genesis transaction in bitcoins. The genesis transaction marks the transacted coins as colored coins, representing your asset. First we must therefore transfer bitcoin into the wallet, so that the wallet has some bitcoin it can use to create a genesis transaction with.

Real bitcoins or testnet bitcoins?
You can use either for this example. If using real bitcoins, you will lose a bit in transaction fees. If using testnet bitcoins, transactions may be a bit slow, and slow down your work through this tutorial. Make sure the server you have started is configured for real or testnet bitcoins, as per your preferences.

The value of bitcoins in the transaction are not proportional to the value of your asset, you just need to put in enough bitcoin to represent your asset and it's parts. Let's say that we are issuing shares in the Foo company ("Foo, Inc.). The Foo company has 1000 ordinary shares. So we need to issue an asset that can be divided, and bought and sold in 1000 individual parts.

Make sure there is a bitcoin address
-----------------------------------

First check if there is already a bitcoin address in the wallet:

    client.listaddresses('bitcoin')

If it returned a bitcoin address, you can use that. However if you are using a pristine wallet, you must create an address:

    client.newaddress('bitcoin')

This should return a bitcoin address. At any time you can do:

    client.listaddresses('bitcoin')

to see what bitcoin addresses are available for funding.

Fund the bitcoin address
-------------------------

Now transfer the needed amount, which should be above 0.001 btc, (also called 1mBTC or 1000 bits). Make sure to add a transfer fee on top of that so that the full 1mBTC actually does arrive in the wallet. You can use any bitcoin wallet to send bitcoin to the wallet.

Currently, you must ask the server to check the state of the blockchain, and update its records:

    client.scan()

After a while the getbalance command should return the new balance. This may take ten minutes, so it might be a good time for a break, and then try again:

    client.getbalance('bitcoin')
    {u'bitcoin': u'0.001'}


Wait until the wallet signals that it knows about the funding before proceeding to the next step.

Backing up private keys
--------------------------

You can get a list of the private bitcoin keys with:

    client.dumpprivkeys('bitcoin')


Issue the asset
------------------

You should now be able to issue an asset of 1000 shares in "Foo, Inc."

    client.issueasset('foo_inc', 1000)

You have just created your first asset.

The 'issueasset' command has the following parameters (in python syntax):

    issueasset(moniker, quantity, unit="1", scheme="epobc")

moniker and quantity must be set in the JSON-RPC call, while unit and scheme have default values.

moniker - a name the asset should be recognized under by the wallet. An asset can have several monikers. The first moniker given in a list is the primary moniker. If you only give one, that's the primary. The moniker is not stored in the blockchain but is saved in the wallet. It is your handle to manipulating the asset. Different assets in the world can have the same moniker but a wallet cannot have two assets by the same primary moniker. In this example we just give one moniker which will the be the primary, "foo_inc".

quantity - the number of indivisable quantities the asset can be traded in. As an example 1000 would mean the smallest unit you can trade is 1/1000 of the total asset. We choose 1000 here for 1000 shares in our fictive company, which shares you should be able to trade individually.

unit (optional) - how much each smallest quantity represents. Can be 1 for example, and 1 is the default value. In this case we have exactly 1000 shares, so the unit is set to 1, that is if you trade 1/1000 of the asset, that is exactly one share. If we wanted to issue ten million shares that can be traded in lots of 1000, then unit would be 1000 and quantity would be 10000.

scheme (optional) - This has to do with how expressive we need the transactions to be. Default is "epobc", the most expressive color scheme (the other possible value is "obc").

You should get something back like this, but with slightly different values for ```assetid``` and ```color_set```:

    {u'assetid': u'Bf1aXLmTv41pc2',
     u'color_set': [u'epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077'],
     u'monikers': [u'foo_inc'],
     u'unit': 1}

If you are using javascript you should get back the same in JSON format:

    {"assetid": "Bf1aXLmTv41pc2",
     "color_set": ["epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077"],
     "monikers": ["foo_inc"],
     "unit": 1}

This JSON is the definition of your asset.

     In [29]:
    client.issueasset('foo_ingc54', 1000)
    Out[29]:
    {u'assetid': u'Bf1aXLmTv41pc2',
     u'color_set': [u'epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077'],
     u'monikers': [u'foo_ingc54'],
     u'unit': 1}

The asset after it has been created resides on a coloraddress. A coloraddress is simply a bitcoin address with some data added in front of an "@" sign. You can ask for the coloraddress if you want to with:

    client.listaddresses('foo_inc')

If you make mistakes when issuing assets, don't worry too much. The asset only becomes an asset of yours once you decide to legally define it as such.
If you botch some attempts at issuances, all you lose is some Bitcoin transfer fees.

Issuing multiple assets
------------------------

Issuing an asset is a bitcoin transaction, and when issuing an asset Chromawallet takes funds and uses a rather small amount to issue the asset and sends the rest of the output it's spending back to itself as _change_. This means that there are more coins on the move than what is used for issuing the asset. This is how all bitcoin transactions work. This means that if you have issued an asset, it may take some time before you can issue another one, even if you put in enough coins in your wallet to fund more issuances. The coins are simply in a round trip on their way back to your wallet, and they need to be stored under some blocks in the blockchain again before deemed confirmed by chromawallet.

For production use it is recommended to use one wallet and server per asset.

Exporting an asset definition
-----------------------------

The asset definition is now in your wallet. You got it back as JSON when issuing the asset, but you can also make the wallet list it with the ```getasset``` command, using the asset's moniker "foo_inc" as the search key:

    client.getasset('foo_inc')

This will get you back data as such:

    {"assetid": u"Bf1aXLmTv41pc2",
    "color_set": [u"epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077"],
    "monikers": [u"foo_inc"],
    "unit": 1}

In JSON:

    {"assetid": "Bf1aXLmTv41pc2",
     "color_set": ["epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077"],
     "monikers": ["foo_inc"],
     "uni"t: 1}

The JSON data is important since it defines your asset and without it your asset would be lost! The asset definition in JSON should therefore be backed up, and can also be used for _sharing_ the asset definition with other parties and exchanges that may want to trade your asset.

Here is a simple backup to file example, in python:

    import json
    asset_info = client.getasset('foo_inc')
    json.dump(asset_info, 'foo_inc_backup.json')

You can also check that you indeed have 1000 items of "foo_inc".

    client.getbalance('foo_inc')

This should return:

    {u'foo_inc': u'1000'}


Transfer 10 shares of the "Foo, Inc." company to someone else's wallet.
-----------------------------------------------

Ok, let's say you want to send 10 shares to another party. This could be a withdrawal from a shared wallet on an exchange, or part of a trade between you and another party.

In order to transfer 10 shares of "Foo Inc." to someone else, they first need to:

* Get the asset definition.

After that they need to:

* Generate an address for the asset.

And finally *you* need to:

* Send the 10 shares to that address

Importing an asset definition
-------------------

For this exercise you need to set up one more json-rpc server, where you are going to pretend to be the other party, i.e. the person or organisation that you want to transfer the 10 shares to. In this way you will have one server running your wallet, and a new server pretending to be the other party.

You need to use a completely separate instance of chromawallet for this, so make sure you have installed an extra instance where you want it in its own directory, before continuing. Then configure it just as the one you already have, but if you run them on the same computer, let the new server listen to another port, e.g. port 8081.

In every day use for e.g. an exchange it will be more common to import an asset than to create a new one. Assets are transferred in the JSON format. Here is an example of an asset in JSON format:

    {"assetid": "Bf1aXLmTv41pc2",
    "color_set": ["epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077"],
    "monikers": ["foo_inc"],
    "unit": 1}


Yours should look pretty much the same, but with other values for assetid and color_set.


For real-world use, if you got this JSON file from someone else, verify with the issuer what it is they're issuing and what legal framework governs its use and transfer.

Now it is time to import the asset. Use your own JSON that you got when you issued your asset.


Import your asset definition with the ```addassetjson``` command. 

With the pyjsonrpc client all data types should be in python, so you need to convert your JSON to a python dict, before making the RPC call. It will be converted to JSON before being sent over the network (see further down for how to do the addassetjson call in javascript):
:

    other_partys_client.addassetjson({'assetid': "Bf1aXLmTv41pc2",
        'color_set': ["epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077"],
        'monikers': ["foo_inc"],
        'unit': 1})

If you are loading from the file foo_inc.json it could look like this:

    import json
    foo_inc_dict = json.load('foo_inc.json')
    other_partys_client.addassetjson(foo_inc_dict)

Make sure the import worked by calling:

    other_partys_client.getasset('foo_inc')

You can also verify that there is 0 of this asset in the wallet:

    other_partys_client.getbalance('foo_inc')

This should return:

    {u'foo_inc': u'0'}

In Javascript, for the addassetjson call, you need to put the asset's JSON under a "data" key, similar to this:

    var rpc = require('node-json-rpc');
    var client = new rpc.Client({
      port: 8080,
      host: '127.0.0.1',
      path: '/',
    });

    client.call({
        "jsonrpc": "2.0",
        "method": "addassetjson",
        "params": {
          data: {
            assetid: "Bf1aXLmTv41pc2",
            color_set: ["epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077"],
            monikers: ["foo_inc"],
            unit: 1
          },
        },
        "id": 0
      },
      function(err, res) {
        if (err) {
          console.log("Error addasset");
          console.log(err);
        } else {
          console.log("Success addasset"); // but check for error key!
          console.log(res);
        }
      }
    );

Generate an address for the asset
----------------------------------
If everything worked, it is time for the other party to generate an address to which you can transfer the 10 shares.

    other_partys_client.newaddress('foo_inc')

It should return something similar to this:

    u'Bf1aXLmTv41pc2@1Bto2AF2vmPYXfbcD5NHd2Sm1f58YFrXHe'


Send the 10 shares to that address
-----------------------------

Now go back to your server and send the 10 shares over. Use the address you got, not the one in the example below:

    client.send('foo_inc, 'Bf1aXLmTv41pc2@1Bto2AF2vmPYXfbcD5NHd2Sm1f58YFrXHe, 10)

And now 10 shares of the Foo Inc. company have been sent to the other party, progressively confirmed by the Bitcoin block chain.
