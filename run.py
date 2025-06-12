import asyncio
import configparser
import multiprocessing
import sys
from multiprocessing import Manager, Process

from aiohttp import web

from load_balancer import LoadBalancer
from pkg.api import runserver
from pkg.src import Blockchain, MemoryPool, NewBlocks, SecondaryChain, UTXOs, SyncManager


def try_to_kill_process(p):
    try:
        p.kill()
    except:
        pass


async def start_server(load_balancer):
    app = web.Application()
    app.router.add_get('/{tail:.*}', load_balancer.handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, load_balancer.host, load_balancer.port)
    await site.start()
    print(f"Load balancer started on {load_balancer.host}:{load_balancer.port}")
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await runner.cleanup()


def start_load_balancer(port: int, worker_ports: list[int], rps: int):
    lb = LoadBalancer(port=port, worker_ports=worker_ports, rps=rps)
    asyncio.run(start_server(lb))


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
    api_cores = int(config['API'].get('cores', "1"))
    api_rps = int(config['API'].get('rps', "10"))

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
        api_treads = []
        lb_process = None

        try:
            if run_api:
                """Run API"""
                try:
                    multiprocessing.set_start_method("spawn")
                except RuntimeError:
                    pass
                worker_ports = []
                for i in range(api_cores):
                    port = api_port + 1 + i
                    api = Process(target=runserver, args=(utxos, MemPool, db_name, db_host, db_port, port))
                    api.start()
                    api_treads.append(api)
                    worker_ports.append(port)
                lb_process = Process(target=start_load_balancer, args=(api_port, worker_ports, api_rps))
                lb_process.start()

            """ Start Server and Listen for miner requests """
            sync = SyncManager(localHost, localPort, db_name, db_host, db_port, newBlockAvailable, secondaryChain, MemPool, utxos)
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
            for api in api_treads:
                try_to_kill_process(api)
            if lb_process:
                try_to_kill_process(lb_process)
        except Exception as e:
            print("ERROR: ", e)
            try_to_kill_process(startServer)
            for api in api_treads:
                try_to_kill_process(api)
            if lb_process:
                try_to_kill_process(lb_process)
