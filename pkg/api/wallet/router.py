from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from pkg.api.schemas import (
    TransactionsPageResponse,
    TransactionsPage,
    ErrorResponse,
    ValidWalletResult,
    ValidWalletResponse,
    WalletResponse,
    WalletResult
)
from pkg.src import UTXOs
from pkg.src.mongodb import AsyncBlockchainDB
from pkg.src.utils import decode_base58


class WalletRouter:
    """
    Router for wallet-related operations.
    """

    def __init__(self, db: AsyncBlockchainDB, utxos: UTXOs):
        self.router = APIRouter()
        self.router.add_api_route(
            "/{wallet}",
            self.get_wallet,
            methods=["GET"],
            response_model=WalletResponse,
            summary="Get Wallet Details",
            description="Retrieve details of a wallet, including its balance and associated public key."
        )
        self.router.add_api_route(
            "/{wallet}/validate",
            self.validate_address,
            methods=["GET"],
            response_model=ValidWalletResponse,
            summary="Validate Wallet Address",
            description="Validate if a wallet address is correctly formatted and retrieve its public key."
        )
        self.router.add_api_route(
            "/{wallet}/transactions",
            self.get_transactions,
            methods=["GET"],
            response_model=TransactionsPageResponse,
            summary="Get Wallet Transactions",
            description="Retrieve paginated transactions associated with a specific wallet."
        )
        self.router.add_api_route(
            "/{wallet}/utxos",
            self.get_utxos,
            methods=["GET"],
            response_model=TransactionsPageResponse,
            summary="Get Wallet UTXOs",
            description="Fetch paginated unspent transaction outputs (UTXOs) for a wallet."
        )

        self.db: AsyncBlockchainDB = db
        self.utxos: UTXOs = utxos

    async def get_transactions(
            self,
            wallet: str,
            page: int = 1,
            size: int = 50
    ):
        """
        Retrieve paginated transactions for a wallet.

        Parameters:
        - **wallet** (str): The wallet address.
        - **page** (int): Page number for pagination (default is 1).
        - **size** (int): Number of transactions per page (default is 50).

        Returns:
        - **TransactionsPageResponse**: Paginated transaction data for the wallet.
        """
        public_key = decode_base58(wallet).hex()
        transactions, num = await self.db.find_transactions_by_wallet(public_key, page, size)
        return JSONResponse(content=TransactionsPageResponse(
            data=TransactionsPage(
                data=transactions,
                total=num,
                page=page,
                size=size
            )
        ).dict())

    async def get_wallet(self, wallet: str):
        """
        Retrieve wallet details, including its balance and public key.

        Parameters:
        - **wallet** (str): The wallet address.

        Returns:
        - **WalletResponse**: Details of the wallet, including its balance and public key.

        Raises:
        - **ValueError**: If the wallet address is invalid.
        """
        amount = 0
        try:
            public_key = decode_base58(wallet)
            utxos = self.utxos.get_utxos_by_wallet(public_key)
            for TxId in utxos:
                for tx_out in utxos[TxId].tx_outs:
                    if not tx_out:
                        continue
                    if not tx_out.script_pubkey.cmds[2]:
                        continue
                    if tx_out.script_pubkey.cmds[2] == public_key:
                        amount += tx_out.amount
            wallet_txs = await self.db.get_count_wallet_transactions(public_key.hex())
            return JSONResponse(
                content=WalletResponse(
                    data=WalletResult(
                        amount=amount,
                        wallet_address=wallet,
                        public_key=public_key.hex(),
                        total_txs=wallet_txs
                    )
                ).dict()
            )
        except ValueError as e:
            return JSONResponse(
                content=WalletResponse(
                    data=None,
                    details={"error": str(e)}
                ).dict()
            )

    @staticmethod
    async def validate_address(wallet: str):
        """
        Validate a wallet address and return its public key.

        Parameters:
        - **wallet** (str): The wallet address.

        Returns:
        - **ValidWalletResponse**: Validation status and public key of the wallet.

        Raises:
        - **ValueError**: If the wallet address is invalid.
        """
        try:
            public_key = decode_base58(wallet).hex()
            return JSONResponse(content=ValidWalletResponse(
                data=ValidWalletResult(status=True, public_key=public_key, address=wallet)
            ).dict())
        except ValueError:
            return JSONResponse(content=ValidWalletResponse(
                data=None
            ).dict())

    async def get_utxos(
            self,
            wallet: str,
            page: int = 1,
            size: int = 50
    ):
        """
        Retrieve paginated UTXOs for a wallet.

        Parameters:
        - **wallet** (str): The wallet address.
        - **page** (int): Page number for pagination (default is 1).
        - **size** (int): Number of UTXOs per page (default is 50, maximum is 100).

        Returns:
        - **TransactionsPageResponse**: Paginated UTXO data for the wallet.

        Raises:
        - **HTTPException**: If the requested size exceeds 100.
        """
        if size > 100:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(details={"msg": f"Size must be less than 100"}).dict()
            )
        public_key = decode_base58(wallet)
        utxos = list(self.utxos.get_utxos_by_wallet(public_key).values())
        total = len(utxos)
        utxos = [tx.to_dict() for tx in utxos[size * (page - 1): size * page]]
        return JSONResponse(content=TransactionsPageResponse(data=TransactionsPage(
            total=total,
            page=page,
            size=size,
            data=utxos
        )).dict())
