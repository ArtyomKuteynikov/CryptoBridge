from typing import List

from pydantic import BaseModel

from pkg.api.schemas.main import Transaction, BlockHeader, BlockTransaction


class Block(BaseModel):
    Height: int
    Blocksize: int
    BlockHeader: BlockHeader
    Txcount: int
    Miner: str | None = None
    # Txs: List[Transaction]


class BlockTransactionsPage(BaseModel):
    data: List[BlockTransaction | Transaction]
    total: int
    page: int
    size: int


class BlockResponse(BaseModel):
    status: str = "success"
    data: Block
    details: dict = {}


class BlockPage(BaseModel):
    data: List[Block]
    total: int
    page: int
    size: int


class BlocksResponse(BaseModel):
    status: str = "success"
    data: BlockPage
    details: dict = {}


class BlockTransactionsResponse(BaseModel):
    status: str = "success"
    data: BlockTransactionsPage
    details: dict = {}
