import uvicorn
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
    def __init__(self, utxos: UTXOs, mem_pool: MemoryPool, port: int, db_name: str, db_host: str, db_port: int):
        self.app = FastAPI(title="ChanceBitCoin", version="1.0.0")
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

        self.utxos: UTXOs = utxos
        self.mem_pool: MemoryPool = mem_pool
        self.db_name: str = db_name
        self.db_host: str = db_host
        self.db_port: int = db_port
        self.port: int = port

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

    def run(self):
        """Start API server"""
        db: AsyncBlockchainDB = AsyncBlockchainDB(self.db_name, self.db_host, self.db_port)

        self.app.include_router(
            BlockRouter(db).router,
            prefix="/blocks",
            tags=["Blocks"]
        )
        self.app.include_router(
            WalletRouter(db, self.utxos).router,
            prefix="/wallet",
            tags=["Wallet"]
        )
        self.app.include_router(
            TransactionsRouter(db, self.utxos, self.mem_pool).router,
            prefix="/transactions",
            tags=["Transactions"]
        )
        self.app.include_router(
            NodesRouter(db).router,
            prefix="/nodes",
            tags=["Nodes"]
        )

        uvicorn.run(self.app, host="0.0.0.0", port=self.port)
