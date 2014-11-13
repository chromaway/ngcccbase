# I tend to keep project bash commands I use often in Makefiles for quick 
# autocompletion and to not forget, feel free to extent/change at will.

server_start_testnet:
	@bitcoind -testnet -txindex -daemon

server_stop_testnet:
	@bitcoin-cli stop

run_tests:
	# p2ptrade
	python -m ngcccbase.p2ptrade.tests.test_basic
	python -m ngcccbase.p2ptrade.tests.test_protocol_objects
	python -m ngcccbase.p2ptrade.tests.test_real
	python -m ngcccbase.p2ptrade.tests.test_agent 	# test fails, legit bug?
	python -m ngcccbase.p2ptrade.tests.test_comm
	python -m ngcccbase.p2ptrade.tests.test_ewctrl

# DEBUGGING
# pip install pudb # install debugger
# import pudb; pu.db # set break point
