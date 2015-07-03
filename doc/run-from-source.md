### Running chromawallet from source

You need git, python 2.7 and virtualenv installed.

Checking out chromawallet-server from source

    mkdir chromawallet
    cd chromawallet
    git clone git@github.com:chromaway/ngcccbase.git
    cd ngcccbase
    git checkout develop
    cd ..
    . bin/activate
    python ngcccbase/setup.py develop


The chromawallet-server can be run both from the command line and as a background server. For running from the command line:

    cd ngcccbase
    python ngccc-server.py startserver