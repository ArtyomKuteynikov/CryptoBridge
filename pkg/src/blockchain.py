import copy
import time
from multiprocessing import Process
from typing import List, Tuple, Dict

from logger import init_logger
from pkg.src.core.block import Block
from pkg.src.core.blockheader import BlockHeader
from pkg.src.core.mempool import MemoryPool
from pkg.src.core.newblocks import NewBlocks
from pkg.src.core.secondarychain import SecondaryChain
from pkg.src.core.tx import CoinbaseTx, Tx
from pkg.src.core.utxos import UTXOs
from pkg.src.mongodb import BlockchainDB
from pkg.src.network import SignUpNode, Broadcaster
from pkg.src.utils import merkle_root, target_to_bits, bits_to_target, get_target_and_timestamp, adjust_target, \
    RESET_DIFFICULTY_AFTER_BLOCKS

logger = init_logger("blockchain")

ZERO_HASH = b"\0" * 32
VERSION = 1
INITIAL_TARGET = 0x0000FFFF00000000000000000000000000000000000000000000000000000000


class Blockchain:
    def __init__(
            self,
            utxos: UTXOs,
            mem_pool: MemoryPool,
            new_block_available: NewBlocks,
            secondary_chain: SecondaryChain,
            local_host: str,
            local_port: int,
            db_name: str,
            db_host: str,
            db_port: int,
            parent_node: str,
            mine: bool = True
    ):
        # Global containers
        self.utxos: UTXOs = utxos
        self.MemPool: MemoryPool = mem_pool
        self.newBlockAvailable: NewBlocks = new_block_available
        self.secondaryChain: SecondaryChain = secondary_chain

        # Local containers
        self.spent_transactions: List[Tuple[bytes, int]] = list()
        self.addTransactionsInBlock: List[Tx] = list()
        self.TxIds: List[bytes] = list()
        self.fee: int = 0
        self.BlockSize: int = 0

        # Settings
        self.current_target: int = INITIAL_TARGET
        self.bits: bytes = target_to_bits(INITIAL_TARGET)

        # Node
        self.current_node: str = f"{local_host}:{local_port}"
        self.parent_node: str = parent_node
        self.mine: bool = mine

        # Data bases
        self.db: BlockchainDB = BlockchainDB(db_name, db_host, db_port)
        self.db.init_db()
        self.init_nodes()

        # node tools
        self.register: SignUpNode = SignUpNode(self.current_node, db_name, db_host, db_port, secondary_chain, mem_pool)
        self.syncNode()
        self.broadcaster: Broadcaster = Broadcaster(self.current_node)

    def init_nodes(self):
        self.db.check_db(self.current_node)
        self.db.add_node(self.parent_node)

    def genesis_block(self, miner_address):
        """Generate very first block"""
        block_height = 0
        prev_block_hash = ZERO_HASH
        self.addBlock(block_height, prev_block_hash, miner_address)

    def set_target_difficulty(self):
        """Set target difficulty on chain boot"""
        bits, timestamp = get_target_and_timestamp(self.db.last_block())
        self.bits = bits
        self.current_target = bits_to_target(self.bits)

    def adjust_target_difficulty(self, block_height: int):
        """Adjust target difficulty every N blocks"""
        if block_height and block_height % RESET_DIFFICULTY_AFTER_BLOCKS == 0:
            block = self.db.get_block(block_height-1)
            prev_block = self.db.get_block(block_height - RESET_DIFFICULTY_AFTER_BLOCKS)
            new_target = adjust_target(block, prev_block)
            if new_target:
                self.bits = target_to_bits(new_target)
                self.current_target = new_target

    def read_transaction_from_memory_pool(self):
        """ Read Transactions from Memory Pool"""
        self.addTransactionsInBlock, self.spent_transactions, self.TxIds, self.fee, self.BlockSize = self.MemPool.pick_txs_to_block()

    def LostCompetition(self):
        """Algorithm if another miner has mined the block"""
        delete_block = []
        temp_blocks = self.newBlockAvailable.to_dict()
        for new_block in temp_blocks:
            block = temp_blocks[new_block]
            try:
                self.newBlockAvailable.check_block(block, self.utxos, self.db, self.secondaryChain)
            except Exception as e:
                logger.error(f"CHECKING NEW BLOCK ERROR: {e}")
                self.newBlockAvailable.remove(new_block)
                continue
            delete_block.append(new_block)
            last_block = self.db.last_block()
            if block.validateBlock(last_block, self.bits):
                for idx, tx in enumerate(block.Txs):
                    self.utxos.add(tx)
                    self.utxos.delete(tx.tx_ins)
                    self.MemPool.remove(tx)
                self.db.save_block(block.to_dict())
            else:
                self.resolve_conflict(block)
        self.newBlockAvailable.delete(delete_block)

    def resolve_conflict(self, block: Block):
        """ Resolve the Conflict b/w the Miners """
        if block.Height < self.db.last_block().Height:
            self.secondaryChain.add(block)
            return
        if self.secondaryChain:
            orphan_txs: Dict[str, Tx] = dict()
            valid_txs: List[str] = list()
            add_blocks: List[Block] = list()

            add_blocks.append(block)
            prev_blockhash = block.BlockHeader.prevBlockHash.hex()
            for _ in self.secondaryChain:
                if prev_blockhash in self.secondaryChain:
                    add_blocks.append(self.secondaryChain.get(prev_blockhash))
                    prev_blockhash = self.secondaryChain.get(prev_blockhash).BlockHeader.prevBlockHash.hex()

            blocks_num = self.db.get_count_blocks()

            """Check if all blocks meet target difficulty rule"""
            first_block_height = add_blocks[-1].Height
            prev_block = self.db.get_block(first_block_height - 1)
            if first_block_height % 10:
                dec_block = self.db.get_block((first_block_height // 10) * 10)
            else:
                dec_block = self.db.get_block(first_block_height - RESET_DIFFICULTY_AFTER_BLOCKS)
            if dec_block and prev_block:
                dec_target = dec_block.BlockHeader.bits
                for block in add_blocks[::-1]:
                    if block.Height % 10 == 0:
                        dec_target = target_to_bits(adjust_target(prev_block, dec_block))
                        dec_block = block
                    if not block.check_difficulty(dec_target):
                        self.newBlockAvailable.remove(block.BlockHeader.blockHash.hex())
                        return
                    prev_block = block

            """Check if blockchain up to date"""
            if add_blocks[-1].Height - 1 < blocks_num:
                last_valid_block = self.db.get_block(add_blocks[-1].Height - 1)
                if last_valid_block.BlockHeader.blockHash.hex() == prev_blockhash:
                    logger.info("CONFLICT RESOLVED")
                    for valid_block in add_blocks:
                        if blocks_num > valid_block.Height:
                            orphan_block = self.db.get_block(valid_block.Height)
                            for tx in orphan_block.Txs:
                                self.utxos.remove(tx)
                                if tx.is_coinbase():
                                    continue
                                for tx_in in tx.tx_ins:
                                    prev_tx = self.db.find_transaction(tx_in.prev_tx.hex())
                                    if prev_tx:
                                        if tx_in.prev_tx.hex() in self.utxos:
                                            tx = self.utxos.get(tx_in.prev_tx.hex())
                                            tx.tx_outs[tx_in.prev_index] = prev_tx.tx_outs[tx_in.prev_index]
                                            self.utxos.add(tx)
                                        else:
                                            self.utxos.add(prev_tx)
                                orphan_txs[tx.id()] = tx
                            self.secondaryChain.add(orphan_block)

                    for add_block in add_blocks[::-1]:
                        valid_block = copy.deepcopy(add_block)
                        for index, tx in enumerate(valid_block.Txs):
                            tx.TxId = tx.id()
                            self.utxos.add(tx)
                            self.utxos.delete(tx.tx_ins)
                            if not tx.is_coinbase():
                                valid_txs.append(valid_block.Txs[index].id())
                        self.db.save_block(valid_block.to_dict())

                    for TxId in orphan_txs:
                        if TxId not in valid_txs:
                            try:
                                self.MemPool.add(orphan_txs[TxId])
                            except Exception as e:
                                logger.error(f"Incorrect transaction {e}")
            else:
                """Update blockchain and try again"""
                self.syncNode()
                blocks_num = self.db.get_count_blocks()
                if add_blocks[-1].Height - 1 < blocks_num:
                    self.resolve_conflict(block)
            self.secondaryChain.delete(add_blocks)

        self.secondaryChain.add(block)

    def wait_for_new_block(self):
        while True:
            if self.newBlockAvailable:
                return

    def addBlock(self, block_height, prev_block_hash, miner_address):
        self.secondaryChain.clear(block_height)
        self.read_transaction_from_memory_pool()

        coinbase = CoinbaseTx(block_height, miner_address)
        coinbaseTx = coinbase.build(block_height)
        self.BlockSize += len(coinbaseTx.serialize())
        coinbaseTx.tx_outs[0].amount = coinbaseTx.tx_outs[0].amount + self.fee
        coinbaseTx.TxId = coinbaseTx.id()
        self.TxIds.insert(0, bytes.fromhex(coinbaseTx.id()))
        self.addTransactionsInBlock.insert(0, coinbaseTx)

        merkleRoot = merkle_root(self.TxIds)[::-1]
        self.adjust_target_difficulty(block_height)
        block_header = BlockHeader(
            version=VERSION,
            prev_block_hash=prev_block_hash,
            merkle_root=merkleRoot,
            timestamp=int(time.time()),
            bits=self.bits,
            nonce=0
        )
        if self.mine:
            competition_over = block_header.mine(self.current_target, self.newBlockAvailable)
        else:
            competition_over = True
            self.wait_for_new_block()

        if competition_over:
            self.LostCompetition()
        else:
            new_block = Block(block_height, self.BlockSize, block_header, len(self.addTransactionsInBlock),
                              self.addTransactionsInBlock)
            block = copy.deepcopy(new_block)
            Process(target=self.broadcaster.start_broadcast_block, args=(block, self.db.get_all_nodes())).start()
            self.MemPool.delete(self.TxIds)
            for tx in block.Txs:
                tx.TxId = tx.id()
                self.utxos.add(tx)
                self.utxos.delete(tx.tx_ins)
            logger.info(f"Block {block_height} mined successfully with Nonce value of {block_header.nonce}")
            self.db.save_block(new_block.to_dict())

    def syncNode(self):
        """Get latest version of blockchain data"""
        self.register.sync()

    def main(self, miner_address):
        """Run the blockchain node"""
        last_block = self.db.last_block()
        if last_block is None:
            self.genesis_block(miner_address)
        self.utxos.build(self.db.get_blocks())
        self.register.downloadMemPool()
        self.set_target_difficulty()

        while True:
            start = time.time()
            last_block = self.db.last_block()
            block_height = last_block.Height + 1
            logger.info(f"Current Block Height is is {block_height}")
            prev_block_hash = last_block.BlockHeader.blockHash
            self.addBlock(block_height, prev_block_hash, miner_address)
            logger.info(f"Mine time: {time.time() - start}")
