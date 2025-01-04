from typing import Dict, List

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from pkg.src.core import Tx, Block


class BlockchainDB:
    def __init__(self, db_name: str, host: str, port: int):
        self.client = MongoClient(host, port)
        self.db = self.client[db_name]
        self.blocks_collection = self.db.blocks
        self.transactions_collection = self.db.transactions
        self.nodes_collection = self.db.nodes

    def init_db(self):
        self.blocks_collection.create_index([('Height', -1)], unique=True)
        self.blocks_collection.create_index([('BlockHeader.blockHash', 1)])
        self.transactions_collection.create_index([('TxId', 1)])
        self.nodes_collection.create_index([('node', 1)], unique=True)

    """Statements"""

    def save_block(self, block: Dict):
        try:
            self.blocks_collection.insert_one(block)
            for transaction in block['Txs']:
                transaction['blockHash'] = block['BlockHeader']['blockHash']
                self.transactions_collection.insert_one(transaction)
        except DuplicateKeyError:
            self.update_block(block)

    def update_block(self, block: Dict):
        try:
            block.pop('_id', None)
            old_block = self.blocks_collection.find_one({'Height': block['Height']})
            if old_block.get("BlockHeader"):
                self.transactions_collection.delete_many({"blockHash": old_block['BlockHeader']['blockHash']})
            self.blocks_collection.replace_one({'Height': block['Height']}, block, upsert=False)
            for transaction in block['Txs']:
                transaction['blockHash'] = block['BlockHeader']['blockHash']
                self.transactions_collection.insert_one(transaction)
        except AttributeError:
            self.save_block(block)

    def delete_block(self, height: int):
        self.blocks_collection.delete_one({'Height': height})

    def delete_blocks(self, start: int | None = None, end: int | None = None):
        conditions = dict()
        if start is not None:
            conditions.update({'$gte': start})
        if end is not None:
            conditions.update({'$lte': end})
        self.blocks_collection.delete_many({'Height': conditions})

    """Queries"""
    """Blocks"""

    def get_count_blocks(self) -> int:
        return self.blocks_collection.count_documents({})

    def find_block(self, block_hash: str) -> Block | None:
        block = self.blocks_collection.find_one({'BlockHeader.blockHash': block_hash})
        return Block.to_obj(block) if block else None

    def get_block(self, height: int) -> Block | None:
        block = self.blocks_collection.find_one({'Height': height})
        if not block:
            return None
        return Block.to_obj(block)

    def last_block(self) -> Block | None:
        last_block = self.blocks_collection.find_one({}, sort=[('Height', -1)])
        return Block.to_obj(last_block) if last_block else None

    def get_blocks(self, start: int | None = None, end: int | None = None) -> List[Block]:
        conditions = dict()
        if start is not None:
            conditions.update({'$gte': start})
        if end is not None:
            conditions.update({'$lte': end})
        blocks = self.blocks_collection.find({'Height': conditions} if conditions else {}).sort('Height', 1)
        return [Block.to_obj(block) for block in blocks]

    """Transactions"""

    def find_transaction(self, transaction_id: str) -> Tx:
        tx = self.transactions_collection.find_one({'TxId': transaction_id})
        return Tx.to_obj(tx) if tx else None

    """Nodes"""
    def get_all_nodes(self) -> List[str]:
        nodes = self.nodes_collection.find()
        return [node["node"] for node in nodes]

    def add_node(self, node: str):
        try:
            self.nodes_collection.insert_one({"node": node})
        except DuplicateKeyError:
            pass

    def update_nodes(self, nodes: List[str]):
        self.nodes_collection.delete_many({})
        for node in nodes:
            self.nodes_collection.insert_one({"node": node})

    def check_db(self, current_node: str) -> bool:
        nodes = self.nodes_collection.find().to_list(length=None)
        if len(nodes) == 0:
            return False
        if len(nodes) == 1 and nodes[0]["node"] == current_node:
            return False
        return True
