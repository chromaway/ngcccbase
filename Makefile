# I tend to keep project bash commands I use often in Makefiles for quick
# autocompletion and to not forget, feel free to extent/change at will.

TESTNET_WALLETS := $(shell find | grep -i "testnet\.wallet_.*$$")

bitcoind_testnet_start:
	@bitcoind -testnet -txindex -daemon

bitcoind_testnet_stop:
	@bitcoin-cli --testnet stop

chromanode_testnet:
	python chromanode.py 127.0.0.1:8080 testnet

rescan_all:
	@$(foreach WALLET,$(TESTNET_WALLETS), \
		python ngccc-cli.py --testnet --wallet=$(WALLET) fullrescan; \
	)

# DEBUGGING
# pip install pudb # install debugger
# import pudb; pu.db # set break point
