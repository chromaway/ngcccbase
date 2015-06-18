### Running chromawallet from source


Checking out chromawallet-server from source

    mkdir chromawallet
    cd chromawallet
    virtualenv .
    . bin/activate
    git clone git@github.com:chromaway/ngcccbase.git
    cd ngcccbase
    git checkout develop
    cd ..
    python ngcccbase/setup.py develop


The chromawallet-server can be run both from the command line and as a background server. For running from the command line:

    python ngccc-server.py startserver