from multiprocessing.managers import DictProxy
from typing import List

from pkg.src.core.block import Block


class SecondaryChain:
    MEMORY_SIZE = 50

    def __init__(self, secondary_chain: DictProxy):
        self.secondaryChain: DictProxy[str, Block] = secondary_chain

    def to_dict(self) -> dict:
        """Copy secondary chain into dict"""
        return dict(self.secondaryChain)

    def add(self, block: Block):
        self.secondaryChain[block.BlockHeader.generateBlockHash()] = block

    def __len__(self):
        return len(self.secondaryChain)

    def get(self, block_hash: str) -> Block:
        return self.secondaryChain.get(block_hash)

    def __bool__(self):
        return bool(self.secondaryChain)

    def __iter__(self):
        return iter(self.secondaryChain)

    def remove(self, block: str | bytes | Block):
        try:
            if type(block) is str:
                del self.secondaryChain[block]
            elif type(block) is bytes:
                del self.secondaryChain[block.hex()]
            else:
                del self.secondaryChain[block.BlockHeader.generateBlockHash()]
        except KeyError:
            pass

    def delete(self, blocks: List[Block | str | bytes]):
        """Delete a transactions from the memory pool."""
        for block in blocks:
            self.remove(block)

    def clear(self, height: int):
        for block in self.secondaryChain.values():
            if block.Height < height - self.MEMORY_SIZE:
                del self.secondaryChain[block.BlockHeader.generateBlockHash()]

