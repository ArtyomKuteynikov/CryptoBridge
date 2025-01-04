from pydantic import BaseModel


class WalletResult(BaseModel):
    amount: int
    wallet_address: str
    public_key: str
    total_txs: int = 0


class WalletResponse(BaseModel):
    status: str = "success"
    data: WalletResult | None
    details: dict = {}


class ValidWalletResult(BaseModel):
    status: bool
    public_key: str
    address: str


class ValidWalletResponse(BaseModel):
    status: str = "success"
    data: ValidWalletResult | None
    details: dict = {}
