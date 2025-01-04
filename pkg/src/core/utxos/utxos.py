from multiprocessing.managers import DictProxy
from typing import List, Dict, Tuple, Set

from pkg.src.core.tx import Tx, TxIn


class UTXOs:
    def __init__(self, utxos: DictProxy, index: DictProxy):
        self.utxos: DictProxy[str, Tx] = utxos
        self.wallet_index: DictProxy[bytes: Set[str]] = index

    def to_dict(self) -> Dict[str, Tx]:
        return dict(self.utxos)

    def __contains__(self, tx_id: str) -> bool:
        return tx_id in self.utxos

    def add(self, tx: Tx):
        """Add tx to UTXOs"""
        self.utxos[tx.TxId] = tx
        self.add_index(tx)

    def add_txs(self, txs: List[Tx]):
        """Add unspent transactions"""
        for tx in txs:
            self.add(tx)

    def get_utxos_by_wallet(self, wallet: bytes) -> Dict[str, Tx]:
        """Get unspent transactions by wallet"""
        tx_ids = self.wallet_index.get(wallet, [])
        return {self.utxos.get(tx_id).TxId: self.utxos.get(tx_id) for tx_id in tx_ids if self.utxos.get(tx_id)}

    def get(self, tx_id: str) -> Tx:
        """Get unspent transaction"""
        return self.utxos.get(tx_id)

    def remove(self, tx: Tx | TxIn | str | bytes):
        """Remove a transaction from UTXOs."""
        try:
            if type(tx) is str:
                for index, _ in enumerate(self.utxos[tx].tx_outs):
                    self.remove_index(self.utxos[tx], index)
                del self.utxos[tx]
            elif type(tx) is bytes:
                for index, _ in enumerate(self.utxos[tx.hex()].tx_outs):
                    self.remove_index(self.utxos[tx.hex()], index)
                del self.utxos[tx.hex()]
            elif type(tx) is TxIn:
                if len(self.utxos[tx.prev_tx.hex()].tx_outs) - self.utxos[tx.prev_tx.hex()].tx_outs.count(None) > 1:
                    prev_tx = self.get(tx.prev_tx.hex())
                    prev_tx.tx_outs[tx.prev_index] = None
                    self.add(prev_tx)
                else:
                    del self.utxos[tx.prev_tx.hex()]
            else:
                for index, _ in enumerate(self.utxos[tx.TxId].tx_outs):
                    self.remove_index(self.utxos[tx.TxId], index)
                del self.utxos[tx.TxId]
        except KeyError:
            pass

    def delete(self, txs: List[Tx | TxIn | str | bytes]):
        """Delete a transactions from UTXOs."""
        for tx in txs:
            self.remove(tx)

    def build(self, blocks):
        """Build UTXOs from all blockchain data"""
        all_txs = dict()

        """Build all txs dict"""
        for block in blocks:
            block = block
            for tx in block.Txs:
                all_txs[tx.TxId] = tx

        """remove spent transactions"""
        for block in blocks:
            block = block
            for tx in block.Txs:
                for tx_in in tx.tx_ins:
                    if tx_in.prev_tx.hex() != "0000000000000000000000000000000000000000000000000000000000000000":
                        if len(all_txs[tx_in.prev_tx.hex()].tx_outs) < 2:
                            del all_txs[tx_in.prev_tx.hex()]
                        else:
                            tx_outs = all_txs[tx_in.prev_tx.hex()].tx_outs
                            tx_outs[tx_in.prev_index] = None

        for tx in all_txs:
            self.add(all_txs[tx])

    def add_index(self, tx: Tx):
        """Add transaction to index"""
        for tx_out in tx.tx_outs:
            if not tx_out:
                continue
            wallet = tx_out.script_pubkey.cmds[2]
            current_set = self.wallet_index.get(wallet, set())
            current_set.add(tx.TxId)
            self.wallet_index[wallet] = current_set

    def remove_index(self, tx: Tx, tx_index: int):
        """Remove spent transactions from index"""
        try:
            tx_out = tx.tx_outs[tx_index]
            self.wallet_index[tx_out.script_pubkey.cmds[2]].remove(tx.TxId)
        except (KeyError, IndexError):
            pass


