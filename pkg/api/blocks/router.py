from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from pkg.api.schemas import BlocksResponse, BlockPage, BlockResponse, ErrorResponse, BlockTransactionsResponse, \
    BlockTransactionsPage
from pkg.src.mongodb import AsyncBlockchainDB


class BlockRouter:
    """
    Router for block-related operations.
    """

    def __init__(self, db: AsyncBlockchainDB):
        self.router = APIRouter()
        self.router.add_api_route(
            "",
            self.get_blocks,
            methods=["GET"],
            response_model=BlocksResponse,
            summary="Get Blocks"
        )
        self.router.add_api_route(
            "/hash/{block_hash}",
            self.find_block,
            methods=["GET"],
            response_model=BlockResponse,
            summary="Find Block by Hash"
        )
        self.router.add_api_route(
            "/num/{block_num}",
            self.get_block,
            methods=["GET"],
            response_model=BlockResponse,
            summary="Get Block by Number"
        )
        self.router.add_api_route(
            "/latest",
            self.get_latest_block,
            methods=["GET"],
            response_model=BlockResponse,
            summary="Get Latest Block"
        )
        self.router.add_api_route(
            "/transactions/{block_hash}",
            self.get_block_transactions,
            methods=["GET"],
            response_model=BlockTransactionsResponse,
            summary="Get Transactions by Block Hash"
        )

        self.db: AsyncBlockchainDB = db

    async def get_blocks(
            self,
            page: int = 1,
            size: int = 50
    ):
        """
        Retrieve paginated blockchain blocks, ordered from the latest to the earliest.

        Parameters:
        - **page** (int): Page number for pagination (default is 1).
        - **size** (int): Number of blocks per page (default is 50).

        Returns:
        - **BlocksResponse**: Paginated block data.
        """
        total = await self.db.get_count_blocks()
        start = (page - 1) * size
        end = start + size
        blocks = await self.db.get_blocks(total - end, total - start)

        return JSONResponse(
            content=BlocksResponse(
                data=BlockPage(
                    data=blocks,
                    page=page,
                    size=size,
                    total=total
                )
            ).dict()
        )

    async def find_block(self, block_hash: str):
        """
        Find a specific block using its unique hash.

        Parameters:
        - **block_hash** (str): The hash of the block to find.

        Returns:
        - **BlockResponse**: Block data if found.

        Raises:
        - **HTTPException**: If the block is not found.
        """
        block = await self.db.find_block(block_hash)
        if block:
            return JSONResponse(content=BlockResponse(data=block).dict())
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(details={"msg": f"Block not found"}).dict()
        )

    async def get_block(self, block_num: int):
        """
        Retrieve a block by its number in the blockchain.

        Parameters:
        - **block_num** (int): The number of the block to retrieve.

        Returns:
        - **BlockResponse**: Block data if found.

        Raises:
        - **HTTPException**: If the block is not found.
        """
        block = await self.db.get_block(block_num)
        if block:
            return JSONResponse(content=BlockResponse(data=block).dict())
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(details={"msg": f"Block not found"}).dict()
        )

    async def get_latest_block(self):
        """
        Fetch the latest block added to the blockchain.

        Returns:
        - **BlockResponse**: The latest block data.

        Raises:
        - **HTTPException**: If the block is not found.
        """
        block = self.db.last_block()
        if block:
            return JSONResponse(content=BlockResponse(data=block).dict())
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(details={"msg": f"Block not found"}).dict()
        )

    async def get_block_transactions(
            self,
            block_hash: str,
            page: int = 1,
            size: int = 50
    ):
        """
        Retrieve paginated transactions from block.

        Parameters:
        - **block_hash** (str): The hash of the block to find.
        - **page** (int): Page number for pagination (default is 1).
        - **size** (int): Number of blocks per page (default is 50).

        Returns:
        - **BlockTransactionsResponse**: Paginated block data.
        """
        total = await self.db.get_count_transactions(block_hash)
        start = (page - 1) * size
        end = start + size
        transactions = await self.db.get_block_transactions(block_hash, start, end)

        return JSONResponse(
            content=BlockTransactionsResponse(
                data=BlockTransactionsPage(
                    data=transactions,
                    page=page,
                    size=size,
                    total=total
                )
            ).dict()
        )
