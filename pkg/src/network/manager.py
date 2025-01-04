from threading import Thread
from typing import Tuple, List

from logger import init_logger
from pkg.src.core import NewBlocks, MemoryPool, SecondaryChain, Tx, Block, UTXOs
from pkg.src.mongodb import BlockchainDB
from pkg.src.network.commands import FinishedSending, NodeList, Handshake
from pkg.src.network.network import NetworkEnvelope
from pkg.src.network.node import Node
from pkg.src.network.requests import RequestBlock, RequestNodes, RequestMemPool, RequestSecondaryChain
from pkg.src.utils import int_to_little_endian, little_endian_to_int

logger = init_logger("manager")


class SyncManager:
    """Network listener"""

    def __init__(
            self,
            host: str,
            port: int,
            db_name: str,
            db_host: str,
            db_port: int,
            new_block_available: NewBlocks,
            secondary_chain: SecondaryChain,
            mem_pool: MemoryPool,
            utxos: UTXOs
    ):
        self.host: str = host
        self.port: int = port
        self.newBlockAvailable: NewBlocks = new_block_available
        self.secondaryChain: SecondaryChain = secondary_chain
        self.memory_pool: MemoryPool = mem_pool
        self.server: Node = Node(self.host, self.port)
        self.utxos: UTXOs = utxos

        self.db_name: str = db_name
        self.db_host: str = db_host
        self.db_port: int = db_port
        self.db: BlockchainDB | None = None

        self.SEND_LIMIT: int = 50

    def spinUpTheServer(self):
        """Run listener node in other tread"""
        if not self.db:
            self.db: BlockchainDB = BlockchainDB(self.db_name, self.db_host, self.db_port)
        self.server.startServer()
        logger.info("SERVER STARTED")
        logger.info(f"LISTENING at {self.host}:{self.port}")
        while True:
            try:
                self.conn, self.addr = self.server.acceptConnection()
                handle_conn = Thread(target=self.handleConnection)
                handle_conn.start()
            except ConnectionResetError:
                pass

    def handleConnection(self):
        """Input requests handler"""
        envelope = self.server.read()

        try:
            if len(str(self.addr[1])) == 4:
                self.addNode()

            if envelope.command == Tx.command:
                transaction = Tx.parse(envelope.stream())
                transaction.TxId = transaction.id()
                try:
                    self.memory_pool.add(transaction)
                except Exception as e:
                    logger.info(f"Incorrect transaction {e}")

            elif envelope.command == Block.command:
                block = Block.parse(envelope.stream())
                try:
                    self.newBlockAvailable.add(block)
                    logger.info(f"New Block Received : {block.Height}")
                except Exception as e:
                    logger.info(f"Incorrect transaction {e}")

            elif envelope.command == RequestBlock.command:
                block = RequestBlock.parse(envelope.stream())
                self.sendBlockToRequestor(block.startBlock)
                logger.info(f"Start Block is {block.startBlock} \n End Block is {block.endBlock}")

            elif envelope.command == RequestNodes.command:
                self.sendNodeList()

            elif envelope.command == RequestMemPool.command:
                self.sendMemoryPool()

            elif envelope.command == RequestSecondaryChain.command:
                self.sendSecondaryChain()

            elif envelope.command == Handshake.command:
                self.sendHandshake()

            else:
                self.sendFinishedMessage()

            self.conn.close()
        except Exception as e:
            self.conn.close()
            logger.error(f"Error while processing the client request {e} {envelope.command}")

    def addNode(self):
        """Add new node to database"""
        port_list = self.db.get_all_nodes()
        addr = f"{self.addr[0]}:{self.addr[1]}"
        if addr not in port_list:
            self.db.add_node(addr)

    def sendBlockToRequestor(self, start_block):
        """
        Send blocks to outer node
        Sends limited number of blocks from start block onу by one
        """
        start_block = little_endian_to_int(start_block)
        blocks, blocks_num = self.fetchBlocksFromBlockchain(start_block)
        self.sendBlock(blocks)
        self.sendFinishedMessage(int_to_little_endian(blocks_num, 4))

    def sendHandshake(self):
        handshake = Handshake()
        envelope = NetworkEnvelope(handshake.command, handshake.serialize())
        self.conn.sendall(envelope.serialize())

    def sendNodeList(self):
        """Send node DB data"""
        node_list = self.db.get_all_nodes()
        node_list = NodeList(node_list)
        envelope = NetworkEnvelope(node_list.command, node_list.serialize())
        self.conn.sendall(envelope.serialize())

    def sendSecondaryChain(self):
        """Send secondary chain to outer node"""
        temp_sec_chain = self.secondaryChain.to_dict()
        for block in temp_sec_chain.values():
            envelope = NetworkEnvelope(block.command, block.serialize())
            self.conn.sendall(envelope.serialize())
        self.sendFinishedMessage()

    def sendMemoryPool(self):
        """Send memory pool to outer node"""
        mem_pool = self.memory_pool.to_dict()
        for tx in mem_pool.values():
            envelope = NetworkEnvelope(tx.command, tx.serialize())
            self.conn.sendall(envelope.serialize())
        self.sendFinishedMessage()

    def sendFinishedMessage(self, param: bytes | None = None):
        """
        Send finished message
        Can handle custom parameter in bytes form
        """
        finish = FinishedSending()
        envelope = NetworkEnvelope(finish.command, finish.serialize(param))
        self.conn.sendall(envelope.serialize())

    def sendBlock(self, blocks_to_send):
        """Send single block to outer node"""
        for block in blocks_to_send:
            envelope = NetworkEnvelope(block.command, block.serialize())
            self.conn.sendall(envelope.serialize())
            logger.info(f"Block Sent {block.Height}")

    def fetchBlocksFromBlockchain(self, start_block: int) -> Tuple[List[dict], int]:
        """Get blocks to send"""
        blocks_to_send = self.db.get_blocks(start_block, start_block + self.SEND_LIMIT)
        blocks_num = self.db.get_count_blocks()
        return blocks_to_send, blocks_num
