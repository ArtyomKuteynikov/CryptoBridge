import asyncio

from hypercorn.asyncio import serve
from hypercorn.config import Config

from pkg.api.main import API
from pkg.src import UTXOs, MemoryPool


def runserver(utxos: UTXOs, mem_pool: MemoryPool, config: Config, db_name: str, db_host: str, db_port: int):
    """Function to run API server in a separate thread."""
    api = API()
    app = api.run(utxos, mem_pool, db_name, db_host, db_port)

    asyncio.run(serve(app, config))


__all__ = ['runserver']
