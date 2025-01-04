import configparser
import multiprocessing
import sys
from multiprocessing import Manager, Process

from pkg.api import runserver
from pkg.src import Blockchain, MemoryPool, NewBlocks, SecondaryChain, UTXOs, SyncManager


def try_to_kill_process(p):
    try:
        p.kill()
    except:
        pass


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()
    config = configparser.ConfigParser()
    config.read('config.ini')

    """Miner"""
    localHost = config['NODE']['host']
    localPort = int(config['NODE'].get('port', "1111"))
    minerWallet = config['NODE'].get('wallet', "")
    mine = bool(int(config['NODE'].get('mine', "1")))

    """Database"""
    db_name = config['DB']['db_name']
    db_host = config['DB']['db_host']
    db_port = int(config['DB']['db_port'])

    """API"""
    api_port = int(config['API'].get('port', "5000"))
    run_api = bool(int(config['API'].get('active', "0")))

    """Parent Node"""
    if config.get("PARENT", "host"):
        parentHost = config['PARENT']['host']
        parentPort = int(config['PARENT'].get('port', "1111"))
    else:
        parentHost, parentPort = localHost, localPort

    with Manager() as manager:
        utxos = UTXOs(manager.dict(), manager.dict())
        MemPool = MemoryPool(manager.dict(), utxos)
        newBlockAvailable = NewBlocks(manager.dict())
        secondaryChain = SecondaryChain(manager.dict())

        try:
            if run_api:
                """Run API"""
                api = Process(target=runserver, args=(utxos, MemPool, api_port, db_name, db_host, db_port))
                api.start()

            """ Start Server and Listen for miner requests """
            sync = SyncManager(localHost, localPort, db_name, db_host, db_port, newBlockAvailable, secondaryChain,
                               MemPool, utxos)
            startServer = Process(target=sync.spinUpTheServer)

            """Run blockchain"""
            blockchain = Blockchain(
                utxos,
                MemPool,
                newBlockAvailable,
                secondaryChain,
                localHost,
                localPort,
                db_name,
                db_host,
                db_port,
                parent_node=f"{parentHost}:{parentPort}",
                mine=mine
            )
            startServer.start()
            blockchain.main(minerWallet)
        except (KeyboardInterrupt, InterruptedError, SystemExit):
            try_to_kill_process(startServer)
            if run_api:
                try_to_kill_process(api)
        except Exception as e:
            print("ERROR: ", e)
            try_to_kill_process(startServer)
            if run_api:
                try_to_kill_process(api)
