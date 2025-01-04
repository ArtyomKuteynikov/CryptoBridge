import asyncio
from typing import List

from logger import init_logger
from pkg.src.core import Block, Tx
from pkg.src.network import Publisher

logger = init_logger("broadcaster")


class Broadcaster:
    def __init__(self, current_node: str):
        self.current_node: str = current_node

    def start_broadcast_block(self, block, nodes: List[str]):
        """Wrapper to run async broadcast_tx in a new process."""
        asyncio.run(self.broadcast_block(block, nodes))

    async def broadcast_block(self, block: Block, nodes: List[str]):
        """Broadcast tx to other nodes asynchronously."""
        tasks = [self.send_block(block, node) for node in nodes if self.current_node != node]
        await asyncio.gather(*tasks)

    @staticmethod
    async def send_block(block: Block, node: str):
        """Send block to node"""
        try:
            host, port = node.split(":")
            sync = Publisher(host, int(port))
            await asyncio.to_thread(sync.publishBlock, block)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"ERROR BROADCASTING BLOCK TO NODE {node}: {e}")

    def start_broadcast_tx(self, tx: Tx, nodes: List[str]):
        """Wrapper to run async broadcast_tx in a new process."""
        asyncio.run(self.broadcast_tx(tx, nodes))

    async def broadcast_tx(self, tx: Tx, nodes: List[str]):
        """Broadcast tx to other nodes asynchronously."""
        tasks = [self.send_tx(tx, node) for node in nodes if self.current_node != node]
        await asyncio.gather(*tasks)

    @staticmethod
    async def send_tx(tx: Tx, node: str):
        """Send tx to node"""
        try:
            host, port = node.split(":")
            sync = Publisher(host, int(port))
            await asyncio.to_thread(sync.publishTx, tx)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"ERROR BROADCASTING TX TO NODE {node}: {e}")
