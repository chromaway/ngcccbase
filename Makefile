# I tend to keep project bash commands I use often in Makefiles for quick
# autocompletion and to not forget, feel free to extent/change at will.

TESTNET_WALLETS := $(shell find | grep -i "testnet\.wallet_.*$$")

bitcoind_testnet_start:
	@bitcoind -testnet -txindex -daemon

bitcoind_testnet_stop:
	@bitcoin-cli --testnet stop

run_tests:
	# p2ptrade
	python -m ngcccbase.p2ptrade.tests.test_basic
	python -m ngcccbase.p2ptrade.tests.test_protocol_objects
	python -m ngcccbase.p2ptrade.tests.test_real
	python -m ngcccbase.p2ptrade.tests.test_agent 	# test fails, legit bug?
	python -m ngcccbase.p2ptrade.tests.test_comm
	python -m ngcccbase.p2ptrade.tests.test_ewctrl

rescan_all:
	@$(foreach WALLET,$(TESTNET_WALLETS), \
		python ngccc-cli.py --testnet --wallet=$(WALLET) full_rescan; \
	)

# DEBUGGING
# pip install pudb # install debugger
# import pudb; pu.db # set break point
