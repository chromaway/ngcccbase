#!/bin/bash

# setup virtualenv
rm -rf /tmp/test_env # remove previous virtualenv
virtualenv -p /usr/bin/python2 /tmp/test_env # create virtualenv
source /tmp/test_env/bin/activate # activate virtualenv
python setup.py develop # install packages

# run test
python -m coloredcoinlib.tests.test_colormap
python -m coloredcoinlib.tests.test_colorset
python -m coloredcoinlib.tests.test_store
python -m coloredcoinlib.tests.test_colorvalue
# FIXME python -m coloredcoinlib.tests.test_colordata
# FIXME python -m coloredcoinlib.tests.test_colordef
# FIXME python -m coloredcoinlib.tests.test_txspec
# FIXME python -m coloredcoinlib.tests.test_builder
python -m coloredcoinlib.tests.test_toposort
# FIXME python -m coloredcoinlib.tests.test_blockchain
python -m ngcccbase.p1ptrade.tests.test_ewctrl
# FIXME python -m ngcccbase.p2ptrade.tests.test_agent
python -m ngcccbase.p2ptrade.tests.test_real
python -m ngcccbase.p2ptrade.tests.test_utils
python -m ngcccbase.p2ptrade.tests.test_comm
python -m ngcccbase.p2ptrade.tests.color.db
python -m ngcccbase.p2ptrade.tests.test_protocol_objects
python -m ngcccbase.p2ptrade.tests.test_basic
# FIXME python -m ngcccbase.tests.test_asset
# FIXME python -m ngcccbase.tests.test_wallet_controller
# FIXME python -m ngcccbase.tests.test_bip0032
# FIXME python -m ngcccbase.tests.test_address
# FIXME python -m ngcccbase.tests.test_verifier
# FIXME python -m ngcccbase.tests.test_deterministic
# FIXME python -m ngcccbase.tests.test_color
# FIXME python -m ngcccbase.tests.test_wallet_model
# FIXME python -m ngcccbase.tests.test_txdb
# FIXME python -m ngcccbase.tests.test_services
# FIXME python -m ngcccbase.tests.test_txcons
# FIXME python -m ngcccbase.tests.test_blockchain

