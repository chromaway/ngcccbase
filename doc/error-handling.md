Error handling
-----------------------

In case of errors when making JSON-RPC calls, there will be an "error" object in the response. pyjsonrpc will automatically convert the error response to an JSON-RPC exception which you can catch, and with some other libraries such as node-json-rpc you should check for the presence of an error object in the response.

This is how to handle errors with pyjsonrpc, ```e.message``` is the one that may be most of interest:

    import pyjsonrpc
    client = pyjsonrpc.HttpClient(url = "http://localhost:8080")

    try:
        client.dumpconfig()
    except pyjsonrpc.rpcerror.JsonRpcError as e:
        print e.code  # see http://www.jsonrpc.org/specification#error_object

        # Error from the server if an exception is raised during the call.
        if e.code <= -32000 and e.code >= -32099:
            print e.message  # source exception message
            data = json.loads(e.data)
            print data["classname"]  # source exception class name
            print data["repr"]  # source exception repr string
            print data["traceback"]  # source exception traceback

For other clients, this is what the JSON response may look like in case of an error. An error is indicated by the presence of an error object. ```error.message``` may be the attribute of most interest:

    { jsonrpc: '2.0',
      id: 0,
      error: 
       { message: 'Not enough coins: : 1000004840 requested, : 256670 found!',
         code: -32000,
         data: '{"classname": "InsufficientFundsError", "traceback": "Traceback (most recent call last): [...] "}' } }