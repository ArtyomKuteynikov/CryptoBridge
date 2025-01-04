from copy import deepcopy
from io import BytesIO
from socket import SocketIO
from typing import List

from pkg.src.core.tx import Tx
from pkg.src.core.blockheader import BlockHeader
from pkg.src.utils import read_varint, encode_varint, little_endian_to_int, int_to_little_endian


class Block:
    """
    Block is a storage container that stores transactions
    """
    command = b'newBlockAvbl'

    def __init__(self, height: int, block_size: int, block_header: BlockHeader, tx_count: int, txs: List[Tx]):
        self.Height: int = height
        self.Blocksize: int = block_size
        self.BlockHeader: BlockHeader = block_header
        self.Txcount: int = tx_count
        self.Txs: List[Tx] = txs

    @classmethod
    def parse(cls, s: SocketIO | BytesIO) -> 'Block':
        """Parse block from socketio stream"""
        height = little_endian_to_int(s.read(4))
        block_size = little_endian_to_int(s.read(4))
        block_header = BlockHeader.parse(s)
        block_header.blockHash = bytes.fromhex(block_header.generateBlockHash())
        tx_count = read_varint(s)
        transactions = []
        for _ in range(tx_count):
            transactions.append(Tx.parse(s))
        return cls(height, block_size, block_header, tx_count, transactions)

    def serialize(self) -> bytes:
        """Convert Block to bytes"""
        result = int_to_little_endian(self.Height, 4)
        result += int_to_little_endian(self.Blocksize, 4)
        result += self.BlockHeader.serialize()
        result += encode_varint(len(self.Txs))

        for tx in self.Txs:
            result += tx.serialize()

        return result

    @classmethod
    def to_obj(cls, last_block: dict) -> 'Block':
        """Parse Block object from dict"""
        block = BlockHeader(
            last_block['BlockHeader']['version'],
            bytes.fromhex(last_block['BlockHeader']['prevBlockHash']),
            bytes.fromhex(last_block['BlockHeader']['merkleRoot']),
            last_block['BlockHeader']['timestamp'],
            bytes.fromhex(last_block['BlockHeader']['bits'])
        )
        block.nonce = last_block['BlockHeader']['nonce']
        transactions = []
        for tx in last_block['Txs']:
            transactions.append(Tx.to_obj(tx))
        block.blockHash = bytes.fromhex(last_block['BlockHeader']['blockHash'])
        return cls(last_block['Height'], last_block['Blocksize'], block, len(transactions), transactions)

    def to_dict(self) -> dict:
        """Convert Block to dict"""
        dt = deepcopy(self.__dict__)
        dt['BlockHeader'] = dt['BlockHeader'].to_dict()
        for tx_id, tx in enumerate(dt['Txs']):
            dt['Txs'][tx_id] = tx.to_dict()
        return dt

    def validateBlock(self, last_block: 'Block', target: bytes = b"") -> bool:
        """Check if block is valid (last block hash and PoW is valid)"""

        if not last_block and self.BlockHeader.prevBlockHash.hex() == "0" * 64:
            return True

        if self.BlockHeader.bits > target and target:
            return False

        if self.BlockHeader.prevBlockHash.hex() == last_block.BlockHeader.blockHash.hex():
            if self.BlockHeader.check_pow():
                return True

    def check_difficulty(self, dec_target: bytes) -> bool:
        """Check if the block meet difficulty rule"""
        if self.BlockHeader.bits <= dec_target:
            return True
