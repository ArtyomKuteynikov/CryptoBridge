from typing import Dict, List, Tuple

from pymongo import AsyncMongoClient

from pkg.src.utils import encode_base58_checksum


class AsyncBlockchainDB:
    def __init__(self, db_name: str, host: str, port: int):
        self.client = AsyncMongoClient(host, port)
        self.db = self.client[db_name]
        self.blocks_collection = self.db.blocks
        self.transactions_collection = self.db.transactions
        self.nodes_collection = self.db.nodes

    async def add_tx_in_details(self, tx: Dict) -> Dict:
        for tx_in in tx["tx_ins"]:
            if tx_in["prev_tx"] == "0" * 64:
                continue
            prev_tx = await self.find_transaction(tx_in["prev_tx"])
            if not prev_tx:
                tx_in["amount"] = 0
                tx_in["script_pubkey"] = "0" * 64
                continue
            prev_tx = prev_tx["tx_outs"][tx_in["prev_index"]]
            tx_in["amount"] = prev_tx["amount"]
            tx_in["script_pubkey"] = prev_tx["script_pubkey"]
            try:
                tx_in["script_pubkey"]["cmds"][2] = encode_base58_checksum(
                    b"\x1c" + bytes.fromhex(tx_in["script_pubkey"]["cmds"][2]))
            except ValueError:
                pass
        for tx_out in tx["tx_outs"]:
            try:
                tx_out["script_pubkey"]["cmds"][2] = encode_base58_checksum(
                    b"\x1c" + bytes.fromhex(tx_out["script_pubkey"]["cmds"][2]))
            except ValueError:
                pass
        return tx

    """Blocks"""

    async def get_count_blocks(self) -> int:
        return await self.blocks_collection.count_documents({})

    async def find_block(self, block_hash: str) -> Dict:
        return await self.blocks_collection.find_one({'BlockHeader.blockHash': block_hash})

    async def get_block(self, height: int) -> Dict:
        return await self.blocks_collection.find_one({'Height': height})

    async def last_block(self) -> Dict:
        return await self.blocks_collection.find_one({}, sort=[('Height', -1)])

    async def get_blocks(self, start: int | None = None, end: int | None = None):
        conditions = dict()
        if start is not None:
            conditions.update({'$gte': start})
        if end is not None:
            conditions.update({'$lte': end})
        blocks = await self.blocks_collection.find({'Height': conditions} if conditions else {},
                                                   sort=[('Height', -1)]).to_list(length=None)
        for block in blocks:
            block['Miner'] = encode_base58_checksum(
                b"\x1c" + bytes.fromhex(block['Txs'][0]['tx_outs'][0]['script_pubkey']['cmds'][2])
            )
        return blocks

    async def get_count_transactions(self, block_hash: str) -> int:
        return await self.transactions_collection.count_documents({'BlockHash': block_hash})

    async def get_count_wallet_transactions(self, wallet: str) -> int:
        total_pipeline = [
            {'$match': {'tx_outs': {'$elemMatch': {'script_pubkey.cmds': wallet}}}},
            {'$unionWith': {
                'coll': 'transactions',
                'pipeline': [
                    {'$lookup': {
                        'from': 'transactions',
                        'localField': 'tx_ins.prev_tx',
                        'foreignField': 'TxId',
                        'as': 'linked_txs'
                    }},
                    {'$match': {'linked_txs.tx_outs': {'$elemMatch': {'script_pubkey.cmds': wallet}}}}
                ]
            }},
            {'$group': {
                '_id': '$TxId'
            }},
            {'$count': 'total'}
        ]
        total_result = await (await self.transactions_collection.aggregate(total_pipeline)).to_list(length=1)
        total = total_result[0]['total'] if total_result else 0
        return total

    async def get_block_transactions(self, block_hash: str, start: int | None = None, end: int | None = None) -> List[Dict]:
        txs = (await self.transactions_collection.find(
            {'blockHash': block_hash}
        ).skip(start).limit(end - start).to_list(length=None))
        for index, tx in enumerate(txs):
            txs[index] = await self.add_tx_in_details(tx)
        return txs

    """Transactions"""

    async def get_transactions(self, start: int | None = None, end: int | None = None) -> Tuple[List[Dict], int]:
        total = await self.transactions_collection.count_documents({})
        txs = (await self.transactions_collection.find(
            sort=[('timestamp', -1)]
        ).skip(start).limit(end - start).to_list(length=None))
        txs = txs
        for index, tx in enumerate(txs):
            txs[index] = await self.add_tx_in_details(tx)
        return txs, total

    async def find_transaction(self, transaction_id: str) -> Dict | None:
        tx = await self.transactions_collection.find_one({'TxId': transaction_id})
        if not tx:
            return None
        return tx

    async def find_transactions_by_wallet(self, wallet_address, page, page_size) -> Tuple[List[Dict], int]:
        pipeline = [
            {'$match': {'tx_outs': {'$elemMatch': {'script_pubkey.cmds': wallet_address}}}},
            {'$set': {'side': 'IN'}},
            {'$unionWith': {
                'coll': 'transactions',
                'pipeline': [
                    {'$lookup': {
                        'from': 'transactions',
                        'localField': 'tx_ins.prev_tx',
                        'foreignField': 'TxId',
                        'as': 'linked_txs'
                    }},
                    {'$match': {'linked_txs.tx_outs': {'$elemMatch': {'script_pubkey.cmds': wallet_address}}}},
                    {'$set': {'side': 'OUT'}}
                ]
            }},
            {'$group': {
                '_id': '$TxId',
                'data': {'$first': '$$ROOT'}
            }},
            {'$sort': {'timestamp': 1}},
            {'$skip': page_size * (page - 1)},
            {'$limit': page_size}
        ]

        txs_cursor = await self.transactions_collection.aggregate(pipeline)
        txs = [tx['data'] for tx in await txs_cursor.to_list(length=None)]
        detailed_txs = [await self.add_tx_in_details(tx) for tx in txs]

        total_pipeline = [
            {'$match': {'tx_outs': {'$elemMatch': {'script_pubkey.cmds': wallet_address}}}},
            {'$unionWith': {
                'coll': 'transactions',
                'pipeline': [
                    {'$lookup': {
                        'from': 'transactions',
                        'localField': 'tx_ins.prev_tx',
                        'foreignField': 'TxId',
                        'as': 'linked_txs'
                    }},
                    {'$match': {'linked_txs.tx_outs': {'$elemMatch': {'script_pubkey.cmds': wallet_address}}}}
                ]
            }},
            {'$group': {
                '_id': '$TxId'
            }},
            {'$count': 'total'}
        ]
        total_result = await (await self.transactions_collection.aggregate(total_pipeline)).to_list(length=1)
        total = total_result[0]['total'] if total_result else 0

        return detailed_txs, total

    """Nodes"""

    async def get_all_nodes(self) -> List[str]:
        nodes = await self.nodes_collection.find({}).to_list(length=None)
        return [node["node"] for node in nodes]
