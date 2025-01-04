import asyncio
import time
from multiprocessing import Process
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from pkg.api.schemas import (
    TransactionResponse,
    TransactionsPageResponse,
    TransactionsPage,
    CreateTransaction,
    ErrorResponse,
    Transaction
)
from pkg.api.schemas.transactions import FeeRate
from pkg.api.txs.utils import Send
from pkg.src import MemoryPool, UTXOs
from pkg.src.core import Tx
from pkg.src.mongodb import AsyncBlockchainDB
from pkg.src.network import Broadcaster


class TransactionsRouter:
    """
    Router for managing blockchain transactions.
    """
    def __init__(self, db: AsyncBlockchainDB, utxos: UTXOs, memory_pool: MemoryPool):
        self.router = APIRouter()
        self.router.add_api_route(
            "",
            self.get_transactions,
            methods=["GET"],
            response_model=TransactionsPageResponse,
            summary="Get all transactions"
        )
        self.router.add_api_route(
            "/hash/{transaction_id}",
            self.get_transaction,
            methods=["GET"],
            response_model=TransactionResponse,
            summary="Get Transaction by hash ID"
        )
        self.router.add_api_route(
            "/memory-pool",
            self.get_memory_pool,
            methods=["GET"],
            response_model=TransactionsPageResponse,
            summary="Retrieve Memory Pool Transactions"
        )
        self.router.add_api_route(
            "/fee-rate",
            self.get_fee_rate,
            methods=["GET"],
            response_model=FeeRate,
            summary="Get current fee rate"
        )
        self.router.add_api_route(
            "/create",
            self.create_tx,
            methods=["POST"],
            response_model=TransactionResponse,
            summary="Create a New Transaction"
        )
        self.router.add_api_route(
            "/broadcast",
            self.broadcast_tx,
            methods=["POST"],
            response_model=TransactionResponse,
            summary="Broadcast Transaction"
        )
        self.router.add_api_route(
            "/unverified",
            self.get_tx_from_mem_pool,
            methods=["GET"],
            response_model=TransactionResponse,
            summary="Get Unverified Transaction"
        )

        self.db: AsyncBlockchainDB = db
        self.memory_pool: MemoryPool = memory_pool
        self.utxos: UTXOs = utxos
        self.spent_txs: List[str] = list()

    async def get_transaction(self, transaction_id: str):
        """
        Retrieve detailed information about a specific transaction using its hash ID.

        Parameters:
        - **transaction_id** (str): The unique identifier of the transaction.

        Returns:
        - **TransactionResponse**: The transaction details.
        """
        transaction = await self.db.add_tx_in_details(await self.db.find_transaction(transaction_id))
        if not transaction:
            transaction = self.memory_pool.get(transaction_id)
            if not transaction:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(details={"msg": f"transaction not found"}).dict()
                )
            transaction = await self.db.add_tx_in_details(transaction.to_dict())
            transaction["confirmed"] = False
        return JSONResponse(content=TransactionResponse(data=transaction).dict())

    async def get_transactions(
            self,
            page: int = 1,
            size: int = 50
    ):
        """
        Retrieve all confirmed transactions.

        Parameters:
        - **page** (int): Page number for pagination (default is 1).
        - **size** (int): Number of transactions per page (default is 50).

        Returns:
        - **TransactionsPageResponse**: Paginated transaction data.
        """
        transactions, total = await self.db.get_transactions(size * (page - 1), size * page)
        return JSONResponse(content=TransactionsPageResponse(
            data=TransactionsPage(
                data=transactions,
                total=total,
                page=page,
                size=size
            )
        ).dict())

    async def get_memory_pool(
            self,
            page: int = 1,
            size: int = 50
    ):
        """
        Fetch paginated transactions currently stored in the memory pool.

        Parameters:
        - **page** (int): Page number for pagination (default is 1).
        - **size** (int): Number of transactions per page (default is 50).

        Returns:
        - **TransactionsPageResponse**: Paginated transaction data from the memory pool.
        """
        memory_pool = ([tx.to_dict() for tx in self.memory_pool.to_dict().values()])[::-1][size * (page - 1): size * page]
        for index, tx in enumerate(memory_pool):
            memory_pool[index] = await self.db.add_tx_in_details(tx)
        return JSONResponse(content=TransactionsPageResponse(
            data=TransactionsPage(
                data=memory_pool,
                total=len(self.memory_pool.to_dict()),
                page=page,
                size=size
            )
        ).dict())

    async def get_fee_rate(self):
        """
        Get fee per vByte rate.

        Parameters:

        Returns:
        - **FeeRate**: integer value representing the fee rate in SATs.
        """
        fee_rate = self.memory_pool.get_fee_rate()
        return JSONResponse(content=FeeRate(
            data=fee_rate
        ).dict())

    async def create_tx(
            self,
            stmt: CreateTransaction
    ):
        """
        Create a new transaction with specified details and prepare it for broadcasting.

        Parameters:
        - **stmt** (CreateTransaction): The transaction creation details.

        Returns:
        - **TransactionResponse**: The created transaction details.

        Raises:
        - **HTTPException**: If there are insufficient funds to create the transaction.
        """
        tx = Send(stmt.version, stmt.from_address, stmt.to_address, stmt.amount, self.utxos, self.memory_pool, self.spent_txs)
        if not tx.prepareTransaction():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(details={"msg": f"Insufficient balance"}).dict()
            )
        tx.TxObj.fee = tx.fee
        return JSONResponse(content=TransactionResponse(data=tx.to_dict()).dict())

    async def broadcast_tx(
            self,
            tx: Transaction,
            wait: bool = False
    ):
        """
        Broadcast signed transaction to the network and optionally wait for confirmation.

        Parameters:
        - **tx** (Transaction): The transaction to be broadcasted.
        - **wait** (bool): Whether to wait for transaction confirmation (default is False).

        Returns:
        - **TransactionResponse**: The broadcasted transaction details.
        """
        tx = Tx.to_obj(tx.dict())
        try:
            self.memory_pool.add(tx)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(details={"msg": str(e)}).dict()
            )
        tx.TxId = tx.id()
        nodes = await self.db.get_all_nodes()
        Process(target=Broadcaster("").start_broadcast_tx, args=(tx, nodes)).start()
        if wait:
            while tx.TxId in self.memory_pool:
                await asyncio.sleep(1)
        return JSONResponse(content=TransactionResponse(data=tx.to_dict()).dict())

    async def get_tx_from_mem_pool(
            self,
            tx_hash: str
    ):
        """
        Retrieve an unverified transaction from the memory pool using its hash.

        Parameters:
        - **tx_hash** (str): The hash of the transaction.

        Returns:
        - **TransactionResponse**: The transaction details.

        Raises:
        - **HTTPException**: If the transaction is not found in the memory pool.
        """
        tx = self.memory_pool.get(tx_hash)
        if not tx:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(details={"msg": f"Tx not found"}).dict()
            )
        return JSONResponse(content=TransactionResponse(data=tx.to_dict()).dict())
