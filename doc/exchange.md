Please note that this documentation is a work in progress. [text in square brackets] are placeholders or comments about the development of the documentation, while `<text in angle brackets>` are placeholders for the user's particular setup.

Trying out chromawallet's JSON API for exchange use
===============

Starting and stopping chromawallet from the command line
---------------

The chromawallet can be run both from the command line and as a background server. For running from the command line:

Path to the python you use (the python in the virtual environmnent if you use virtualenv, otherwise the system python)

    </path/to/python> ngccc-server.py startserver

The server will start with configuration parameters found in config.json. If you want to start the server with another config file, add the config_file switch when starting:

    </path/to/python> ngccc-server.py startserver --config_file=<other_config.json>


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

hostname - what interface the server should listen to. "localhost" will only allow connections from a client on localhost. Use e.g. "0.0.0.0" for accepting connections from everywhere.

wallet_path - path to the wallet database. The wallet database is used by the server process. If you specify a path where no file exists, chromawallet will create a new wallet for you there.

testnet - controls whether the wallet should be a testnet wallet, that is operate with bitcoin addresses and colored coins on the testnet3 network, or if the wallet should operate on the real bitcoin network, with real bitcoins. The testnet setting must agree with the wallet you specify on wallet_path. A wallet cannot be switched to and from testnet. If you specify a path that creates a new wallet, the wallet will take its testnet setting from the "testnet" setting. So for a live wallet, ```testnet``` should be set to ```false```.

Running chromawallet as a service/daemon
---------------
You can use supervisord for this.

Supervisord is a framework for running processes and keeping them alive. Read more about it here: http://supervisord.org . Supervisord runs processes that think they are running in the foreground, such as ngccc-server.py but are in fact connected to supervisord. Supervisord can restart and otherwise manage ngccc-server.py, without the need for pid files or other such things.

On Ubuntu, you can install supervisord easily; it is one of the packages in the usual repositories. It is named "supervisor":

    sudo apt-get install supervisor

After supervisord has been installed, it has an entry in the /etc/init.d directory, and in /etc/supervisor/conf.d directory you can add a file with directions for it to run ngccc-server.py . On install supervisord is configured to start immediately and then re-start every time the the server boots.

Below is an example entry in the /etc/supervisorsuper/supervisord.conf file on a Ubuntu 14.04 LTS server for running chromawallet. In this setup example, the install directory is:

    /home/a_user_name/chromawallet_virtual_env

with the python interpreter in

                                         ./bin

and the chromawallet script in

                                         ./ngccc

...inside that directory.

The file is called chromawallet.conf in this example and the user it should run under is "a_user_name":

    [program:chromawallet]
    command=/home/a_user_name/chromawallet_virtual_env/bin/python ngccc-server.py startserver
    process_name=%(program_name)s
    numprocs=1
    directory=/home/a_user/chromawallet_virtual_env/ngccc
    stopsignal=TERM
    user=a_user_name



You can then re-start supervisord to load the new settings: 

    sudo service supervisor restart

Testing that the server is up
-----------------------

You can use a json-rpc library to do this.

Example in python with pyjsonrpc:

    import pyjsonrpc

    client = pyjsonrpc.HttpClient(url = "http://localhost:8080")

    client.dumpconfig()

pyjsonrpc can be found at  ( https://pypi.python.org/pypi/python-jsonrpc )

Creating an asset
-------------------
In order to create an asset with colored coins, you must let the software make a genesis transaction in bitcoins. The genesis transaction marks the transacted coins as colored coins, representing your asset. First we must therefore transfer bitcoin into the wallet, so that the wallet has some bitcoin it can use to create a genesis transaction.

Real bitcoins or testnet bitcoins?
You can use either for this example. If using real bitcoins, you will lose a bit in transaction fees. If using testnet bitcoins, transactions may be a bit slow, and slow down your work through this tutorial. Make sure the server you have started is configured for real or testnet bitcoins, as per your preferences.

The value of bitcoins in the transaction are not proportional to the value of your asset, you just need to put in enough bitcoin to represent your asset and it's parts. Let's say that we are issuing shares in the Foo company ("Foo, Inc.). The Foo company has 1000 ordinary shares. So we need to issue an asset that can be divided, and bought and sold in 1000 individual parts. 

First check if there is already a bitcoin address in the wallet:

    client.listaddresses('bitcoin')

If it returned a bitcoin address, you can use that. However if you are using a pristine wallet, you must create an address:

    client.newaddress('bitcoin')


Now transfer the needed amount, which should be above 0.001 btc, (also called 1mBTC or 1000 bits). Make sure to add a transfer fee on top of that so that the full 1mBTC actually does arrive in the wallet.

You should now be able to issue an asset of 1000 shares in "Foo, Inc."

    client.issueasset('foo_inc', 1000)

You have just created your first asset. 
This asset resides on a coloraddress. A coloraddress is simply a bitcoin address with some info added on what asset is issued there.

'issueasset' has the following parameters:

moniker - a name the asset should be recognized under by the wallet. An asset can have several monikers. The first moniker given in a list is the primary moniker. If you only give one, that's the primary. The moniker is not stored in the blockchain but is saved in the wallet. It is your handle to manipulatimg the asset. Different assets in the world can have the same moniker but a wallet cannot have two assets by the same primary moniker. In this example we just give one moniker which will the be the primary, "fictive_co".

quantity - the number of indivisable quantities the asset can be traded in. As an example 1000 would mean the smallest unit you can trade is 1/1000 of the total asset. We choose 1000 here for 1000 shares in our fictive company, which shares you should be able to trade individually.

unit (optional) - how much each smallest quantity represents. Can be 1 for example. In this case we have exactly 1000 shares, so the unit is set to 1, that is if you trade 1/1000 of the asset, that is exactly one share. If we wanted to issue ten million shares that can be traded in lots of 1000, then unit would be 1000 and quantity would be 10000.

scheme (optional) - This has to do with how expressive we need the transactions to be. Set it to "epobc", the most expressive color scheme (the other possible value is "obc").


    client.issueasset(moniker="fictive_co", quantity = 1000, unit = 1, scheme="epobc" )

Exporting an asset definition
-----------------------------

You can now export a JSON file that contains the definition of your asset.

    client.getasset('foo_inc')

This should return JSON data that can be used for backing up the asset definition, and for sharing the asset definition with other wallets.

Exporting a 

Transfer 10 shares of the "Foo, Inc." company to someone else.
-----------------------------------------------

    send(moniker, coloraddress, amount)

So in this case it will be:

    client.send('foo_inc', <coloraddress>, 10)

You can use our coloradress


Importing an asset definition
-------------------

In every day use for e.g. an exchange it will be more common to import an asset than to create a new one. Assets are transferred in JSON format. Here is an example of an asset.

For real-world use, verify with the issuer what it is they're issuing.

Here is a nothing asset definition you can import [maybe we should have a faucet for a nothing asset, so that exchanges have something to import? That would mean having an extra server up, though.]:









