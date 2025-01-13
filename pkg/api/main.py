from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pkg.api.blocks import BlockRouter
from pkg.api.nodes import NodesRouter
from pkg.api.schemas import ErrorResponse
from pkg.api.txs import TransactionsRouter
from pkg.api.wallet import WalletRouter
from pkg.src import MemoryPool, UTXOs
from pkg.src.mongodb import AsyncBlockchainDB


class API:
    """Blockchain API interface"""
    def __init__(self):
        self.app = FastAPI(title="CryptoBridge Coin", version="1.1.0")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Разрешить запросы с любого источника
            allow_credentials=True,
            allow_methods=["*"],  # Разрешить все HTTP-методы
            allow_headers=["*"],  # Разрешить все заголовки
        )
        self.app.add_event_handler(
            "startup",
            self.startup
        )
        self.app.add_event_handler(
            "shutdown",
            self.shutdown
        )
        self.app.add_exception_handler(
            500,
            self.internal_exception_handler
        )

    @staticmethod
    async def internal_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(details={"msg": f"ERROR: {exc}"}).dict()
        )

    @staticmethod
    async def startup():
        pass

    @staticmethod
    async def shutdown():
        pass

    def run(self, utxos: UTXOs, mem_pool: MemoryPool, db_name: str, db_host: str, db_port: int):
        """Start API server"""
        db: AsyncBlockchainDB = AsyncBlockchainDB(db_name, db_host, db_port)

        self.app.include_router(
            BlockRouter(db).router,
            prefix="/blocks",
            tags=["Blocks"]
        )
        self.app.include_router(
            WalletRouter(db, utxos).router,
            prefix="/wallet",
            tags=["Wallet"]
        )
        self.app.include_router(
            TransactionsRouter(db, utxos, mem_pool).router,
            prefix="/transactions",
            tags=["Transactions"]
        )
        self.app.include_router(
            NodesRouter(db).router,
            prefix="/nodes",
            tags=["Nodes"]
        )
        return self.app
