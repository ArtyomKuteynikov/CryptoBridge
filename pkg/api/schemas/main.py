from typing import List, Union

from pydantic import BaseModel


class ScriptSig(BaseModel):
    cmds: List[Union[int, str]]


class TxIn(BaseModel):
    prev_tx: str
    prev_index: int
    script_sig: ScriptSig
    sequence: int


class ScriptPubKey(BaseModel):
    cmds: List[Union[int, str]]


class TxOut(BaseModel):
    amount: int
    script_pubkey: ScriptPubKey


class BlockTxIn(BaseModel):
    prev_tx: str
    prev_index: int
    script_sig: ScriptSig
    sequence: int
    amount: int
    script_pubkey: ScriptPubKey


class BlockTransaction(BaseModel):
    version: int
    tx_ins: List[BlockTxIn]
    tx_outs: List[TxOut | None]
    locktime: int
    timestamp: int
    confirmed: bool = True
    TxId: str | None
    fee: int | None = None
    blockHash: str | None = None
    side: str | None = None


class Transaction(BaseModel):
    version: int
    tx_ins: List[TxIn]
    tx_outs: List[TxOut | None]
    locktime: int
    timestamp: int
    confirmed: bool = True
    TxId: str | None
    fee: int | None = None
    blockHash: str | None = None
    side: str | None = None


class BlockHeader(BaseModel):
    version: int
    prevBlockHash: str
    merkleRoot: str
    timestamp: int
    bits: str
    nonce: int
    blockHash: str
