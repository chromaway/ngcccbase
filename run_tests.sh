#!/bin/bash

# setup virtualenv
virtualenv -p /usr/bin/python2 env
source env/bin/activate
python setup.py develop

# run test
python -m coloredcoinlib.tests.test_colormap
python -m coloredcoinlib.tests.test_colorset
python -m coloredcoinlib.tests.test_store
python -m coloredcoinlib.tests.test_colorvalue
python -m coloredcoinlib.tests.test_colordata
python -m coloredcoinlib.tests.test_colordef
python -m coloredcoinlib.tests.test_txspec
python -m coloredcoinlib.tests.test_builder
python -m coloredcoinlib.tests.test_toposort
python -m coloredcoinlib.tests.test_blockchain
python -m ngcccbase.p2ptrade.tests.test_ewctrl
python -m ngcccbase.p2ptrade.tests.test_agent
python -m ngcccbase.p2ptrade.tests.test_real
python -m ngcccbase.p2ptrade.tests.test_utils
python -m ngcccbase.p2ptrade.tests.test_comm
python -m ngcccbase.p2ptrade.tests.color.db
python -m ngcccbase.p2ptrade.tests.test_protocol_objects
python -m ngcccbase.p2ptrade.tests.test_basic
python -m ngcccbase.tests.test_asset
python -m ngcccbase.tests.test_wallet_controller
python -m ngcccbase.tests.test_bip0032
python -m ngcccbase.tests.test_address
python -m ngcccbase.tests.test_verifier
python -m ngcccbase.tests.test_deterministic
python -m ngcccbase.tests.test_color
python -m ngcccbase.tests.test_wallet_model
python -m ngcccbase.tests.test_txdb
python -m ngcccbase.tests.test_services
python -m ngcccbase.tests.test_txcons
python -m ngcccbase.tests.test_blockchain

