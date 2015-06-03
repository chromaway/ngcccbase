# I tend to keep project bash commands I use often in Makefiles for quick
# autocompletion and to not forget, feel free to extent/change at will.


TESTNET_WALLETS := $(shell find | grep -i "testnet\.wallet_.*$$")


clean:
	@rm -rf env
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg
	@find | grep -i ".*\.pyc$$" | xargs -r -L1 rm


devsetup: clean
	virtualenv -p /usr/bin/python2 env/ngcccbase
	env/ngcccbase/bin/python setup.py develop
	# setup qt
	cp -r /usr/lib/python2.7/dist-packages/PyQt4 env/ngcccbase/lib/python2.7/site-packages
	cp -r /usr/lib/python2.7/dist-packages/sip* env/ngcccbase/lib/python2.7/site-packages
	mkdir -p env/ngcccbase/share/pyshared
	#cp -r /usr/share/pyshared/PyQt4 env/ngcccbase/share/pyshared


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
