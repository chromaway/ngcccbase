import blockchain
import store
import agent
import builder
import colordef

def test():
    blockchain_state = blockchain.BlockchainState("http://bitcoinrpc:8oso9n8E1KnTexnKHn16N3tcsGpfEThksK4ojzrkzn3b@localhost:18332/")
    store_conn = store.DataStoreConnection("color.db")

    cdstore = store.ColorDataStore(store_conn.conn)
    metastore = store.ColorMetaStore(store_conn.conn)

    genesis = {'txhash': 'b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e',
               'outindex': 0,
               'height': 46442}
               
    colordef1 = colordef.OBColorDefinition(1, genesis)
    colordefman = agent.ColorDefinitionManager()

    cdbuilder = builder.FullScanColorDataBuilder(cdstore, blockchain_state, colordef1, metastore)
    
    mempoolcd = agent.MempoolColorData(blockchain_state)
    cdata = agent.ThickColorData(cdbuilder, mempoolcd, blockchain_state, colordefman, cdstore)

    wallet = agent.CAWallet()

    ccagent = agent.ColoredCoinAgent(blockchain_state, cdata, wallet)
    ccagent.update()

if __name__ == "__main__":
    test()
