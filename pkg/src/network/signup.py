from typing import List, Tuple

from logger import init_logger
from pkg.src.core import Block, Tx, SecondaryChain, MemoryPool
from pkg.src.mongodb import BlockchainDB
from pkg.src.network import Publisher
from pkg.src.network.commands import FinishedSending, NodeList, Handshake
from pkg.src.network.network import NetworkEnvelope
from pkg.src.network.requests import RequestBlock, RequestNodes, RequestMemPool, RequestSecondaryChain
from pkg.src.utils import int_to_little_endian

logger = init_logger("signup")


class SignUpNode:
    """Blockchain data downloader on node boot"""

    def __init__(
            self,
            node: str,
            db_name: str,
            db_host: str,
            db_port: int,
            secondary_chain: SecondaryChain,
            memory_pool: MemoryPool
    ):
        self.secondaryChain: SecondaryChain = secondary_chain
        self.memoryPool: MemoryPool = memory_pool

        self.db: BlockchainDB = BlockchainDB(db_name, db_host, db_port)

        self.nodes: List[str] = list()
        self.last_block: int = int(10e9)

        self.current_node = node
        self.host, self.port = self.nodePicker()
        if self.host and self.port:
            self.downloadNodes()

    def nodePicker(self) -> Tuple[str | None, int | None]:
        nodes = self.db.get_all_nodes()
        for node in nodes:
            if self.current_node == node:
                continue
            host, port = node.split(":")
            if self.sendHandshake(host, int(port), int(self.current_node.split(":")[1])):
                self.nodes.append(node)
        self.db.update_nodes(self.nodes)
        self.db.add_node(self.current_node)
        if not self.nodes:
            return None, None
        return self.nodes[0].split(":")[0], int(self.nodes[0].split(":")[1])

    @staticmethod
    def sendHandshake(host: str, port: int, node: int):
        """Send handshake msg and check node status"""
        try:
            publisher = Publisher(host, port, node)
            handshake = Handshake()
            publisher.sendRequest(handshake)
            envelope = NetworkEnvelope.parse(publisher.stream)
            if envelope.command == handshake.command:
                return Handshake.parse(envelope.stream())
        except Exception as e:
            logger.error(f"NODE {host}:{port} HANDSHAKE ERROR: {e}")
            return False

    def downloadNodes(self):
        """Download all nodes addresses"""
        publisher = Publisher(self.host, self.port)
        publisher.sendRequest(RequestNodes)
        envelope = NetworkEnvelope.parse(publisher.stream)
        if envelope.command == NodeList.command:
            nodes = NodeList.parse(envelope.stream())
            node_list = self.db.get_all_nodes()
            for node in nodes:
                if node not in node_list:
                    host, port = node.split(":")
                    if self.sendHandshake(host, int(port), int(self.current_node.split(":")[1])):
                        self.nodes.append(node)
            self.db.update_nodes(self.nodes)
            self.db.add_node(self.current_node)
        publisher.close()

    def downloadMemPool(self):
        """Download current memory pool"""
        if len(self.nodes) < 1:
            return
        publisher = Publisher(self.host, self.port)
        publisher.sendRequest(RequestMemPool)
        temp_mem_pool = list()
        while True:
            envelope = NetworkEnvelope.parse(publisher.stream)
            if envelope.command == Tx.command:
                transaction = Tx.parse(envelope.stream())
                transaction.TxId = transaction.id()
                temp_mem_pool.append(transaction)
            if envelope.command == FinishedSending.command:
                break
        for transaction in temp_mem_pool:
            try:
                self.memoryPool.add(transaction)
            except Exception as e:
                logger.warning(f"Incorrect transaction {e}")
        publisher.close()

    def downloadSecondaryChain(self):
        """Download current secondary chain data"""
        publisher = Publisher(self.host, self.port)
        headers = RequestSecondaryChain()
        publisher.sendRequest(headers)
        while True:
            envelope = NetworkEnvelope.parse(publisher.stream)
            if envelope.command == Block.command:
                block = Block.parse(envelope.stream())
                self.secondaryChain.add(block)
            if envelope.command == FinishedSending.command:
                break
        publisher.close()

    def startDownloadBlocks(self):
        """
        Download from nodes
        This function downloads blocks by portions from all nodes on chain
        """
        while True:
            for node in self.nodes:
                try:
                    last_block = self.db.last_block()
                    if (last_block.Height + 1 if last_block else 0) >= self.last_block:
                        return
                    if node == self.current_node:
                        continue
                    host, port = node.split(":")
                    publisher = Publisher(host, port)
                    self.downloadBlocks(publisher, last_block)
                except Exception as e:
                    logger.error(f"BLOCKS DOWNLOAD ERROR: ERROR: {e}")

    def downloadBlocks(self, publisher: Publisher, last_block: Block | None):
        """Write received blocks"""
        try:
            start_block = int_to_little_endian((last_block.Height + 1 if last_block else 0), 4)
            headers = RequestBlock(start_block=start_block)
            publisher.sendRequest(headers)
            while True:
                envelope = NetworkEnvelope.parse(publisher.stream)
                if envelope.command == Block.command:
                    block = Block.parse(envelope.stream())
                    if block.validateBlock(last_block):
                        for idx, tx in enumerate(block.Txs):
                            tx.TxId = tx.id()
                            block.Txs[idx] = tx
                        self.db.save_block(block.to_dict())
                        last_block = block
                        logger.info(f"Block Received - {block.Height}")
                    else:
                        logger.warning(f"INVALID BLOCK {block.Height}")
                        if block.BlockHeader.generateBlockHash() in self.secondaryChain:
                            self.db.delete_blocks(block.Height - 50, block.Height - 1)
                            break
                        self.secondaryChain.add(block)
                if envelope.command == FinishedSending.command:
                    self.last_block = FinishedSending.parse(envelope.stream()) or self.last_block
                    break
        except Exception as e:
            logger.error(f"BLOCKS DOWNLOAD ERROR: NODE:{publisher.host}:{publisher.port}, ERROR: {e}")
        finally:
            publisher.close()

    def sync(self):
        """Run downloading latest blockchain data"""
        if len(self.nodes) < 1:
            return
        self.startDownloadBlocks()
        self.downloadSecondaryChain()
