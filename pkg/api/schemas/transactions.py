from typing import List

from pydantic import BaseModel

from pkg.api.schemas.main import Transaction, BlockTransaction


class TransactionResponse(BaseModel):
    status: str = "success"
    data: BlockTransaction | Transaction
    details: dict = {}


class TransactionsPage(BaseModel):
    data: List[BlockTransaction | Transaction]
    total: int
    page: int
    size: int


class TransactionsPageResponse(BaseModel):
    status: str = "success"
    data: TransactionsPage
    details: dict = {}


class FeeRate(BaseModel):
    status: str = "success"
    data: int
    details: dict = {}


class CreateTransaction(BaseModel):
    version: int = 1
    from_address: str
    to_address: str
    amount: int
