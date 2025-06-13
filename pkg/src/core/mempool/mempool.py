import time
from multiprocessing.managers import DictProxy
from typing import List, Dict, Tuple

from pkg.src.core.tx import Tx
from pkg.src.core.utxos import UTXOs


class MemoryPool:
    """Memory pool of transactions"""
    MAX_BLOCK_SIZE = 1024 * 1024
    BASE_FEE = 100000

    def __init__(self, memory_pool: DictProxy, utxos: UTXOs):
        self.MemoryPool: DictProxy[str, Tx] = memory_pool
        self.UTXOs = utxos
        self.prevTxs: List[bytes] = list()

    def __contains__(self, tx_id: str) -> bool:
        return tx_id in self.MemoryPool

    def to_dict(self) -> Dict[str, Tx]:
        """Make a copy of the memory pool."""
        return dict(self.MemoryPool)

    def add(self, tx: Tx):
        """Add a transaction to the memory pool."""
        input_amount = 0
        output_amount = 0
        current_time = int(time.time())
        if not (current_time >= tx.timestamp > current_time - 3600):
            raise Exception("Incorrect timestamp")
        for index, tx_in in enumerate(tx.tx_ins):
            prev_tx = self.UTXOs.get(tx_in.prev_tx.hex())
            if not prev_tx:
                raise Exception("Incorrect input")
            if not prev_tx.tx_outs[tx_in.prev_index]:
                raise Exception("Double spending")
            script = prev_tx.tx_outs[tx_in.prev_index].script_pubkey
            if not tx.verify_input(index, script):
                raise Exception("Verification error")
            input_amount += prev_tx.tx_outs[tx_in.prev_index].amount
        for tx_out in tx.tx_outs:
            output_amount += tx_out.amount
        fee = len(tx.serialize()) * self.get_fee_rate()
        if output_amount >= input_amount + fee:
            raise Exception("Insufficient balance")
        self.MemoryPool[tx.id()] = tx

    def remove(self, tx: Tx | str | bytes):
        """Remove a transaction from the memory pool."""
        try:
            if type(tx) is str:
                del self.MemoryPool[tx]
            elif type(tx) is bytes:
                del self.MemoryPool[tx.hex()]
            else:
                del self.MemoryPool[tx.id()]
        except KeyError:
            pass

    def delete(self, txs: List[Tx | str | bytes]):
        """Delete a transactions from the memory pool."""
        for tx in txs:
            self.remove(tx)

    def get(self, tx_id: str) -> Tx | None:
        """Get a transaction from the memory pool."""
        return self.MemoryPool.get(tx_id)

    def get_fee_rate(self) -> int:
        """Get avg. fee/tx_size rate from memory pool."""
        size = 0
        for tx in self.MemoryPool.values():
            size += tx.size
        return int(max(1, size // self.MAX_BLOCK_SIZE) * self.BASE_FEE)
    
    def double_spending(self, tx: Tx) -> bool:
        """ Check if it is a double spending Attempt """
        for tx_in in tx.tx_ins:
            if tx_in.prev_tx not in self.prevTxs and tx_in.prev_tx.hex() in self.UTXOs:
                if not self.UTXOs.get(tx_in.prev_tx.hex()).tx_outs[tx_in.prev_index]:
                    return True
                self.prevTxs.append(tx_in.prev_tx)
            else:
                return True

    def sorted_txs(self) -> List[Tx]:
        txs = list()
        for tx in self.MemoryPool.values():
            txs.append(tx)
        return sorted(txs, key=lambda tx: tx.calculate_fee(self.UTXOs)/tx.size)

    def pick_txs_to_block(self) -> Tuple[List[Tx], List[Tuple[bytes, int]], List[bytes], int, int]:
        added_transactions = list()
        spent_transactions = list()
        tx_ids = list()
        fee = 0
        block_size = 80
        for tx in self.sorted_txs():
            if block_size + tx.size > self.MAX_BLOCK_SIZE:
                return added_transactions, spent_transactions, tx_ids, fee, block_size
            if not self.double_spending(tx):
                block_size += tx.size
                added_transactions.append(tx)
                tx_ids.append(tx.hash())
                fee += tx.fee
                for spent in tx.tx_ins:
                    spent_transactions.append((spent.prev_tx, spent.prev_index))
            else:
                self.remove(tx)
        self.prevTxs = list()
        return added_transactions, spent_transactions, tx_ids, fee, block_size

    def __iter__(self):
        return self.MemoryPool.__dict__
