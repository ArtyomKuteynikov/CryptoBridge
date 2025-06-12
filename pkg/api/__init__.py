import uvicorn

from pkg.api.main import API
from pkg.src import UTXOs, MemoryPool


def runserver(utxos: UTXOs, mem_pool: MemoryPool, db_name: str, db_host: str, db_port: int, port: int):
    """Function to run API server in a separate thread."""
    api = API()
    app = api.run(utxos, mem_pool, db_name, db_host, db_port)

    uvicorn.run(app, host="localhost", port=port)


__all__ = ['runserver']
