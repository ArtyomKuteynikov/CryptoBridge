from pkg.api.main import API
from pkg.src import UTXOs, MemoryPool


def runserver(utxos: UTXOs, mem_pool: MemoryPool, port: int, db_name: str, db_host: str, db_port: int):
    """Function to run API server in a separate thread."""
    api = API(utxos, mem_pool, port, db_name, db_host, db_port)
    api.run()


__all__ = ['runserver']
