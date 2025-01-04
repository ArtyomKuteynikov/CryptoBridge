import time
from typing import List

from pkg.src import UTXOs, MemoryPool
from pkg.src.core import Script, TxIn, TxOut, Tx
from pkg.src.utils import decode_base58


class Send:
    """Transaction creator"""
    COIN = 100000000

    def __init__(
            self,
            version: int,
            from_address: str,
            to_address: str,
            amount: float,
            utxos: UTXOs,
            memory_pool: MemoryPool,
            spent_txs: List,
    ):
        self.version: int = version
        self.script_key = self.scriptPubKey(from_address)
        self.pubkey = self.script_key.cmds[2]
        self.toAccount = to_address
        self.Amount = int(amount * self.COIN)

        self.utxos = utxos
        self.memory_pool = memory_pool

        self.TxObj: Tx | None = None
        self.isBalanceEnough: bool = False
        self.fee: int = 0
        self.Total: int = 0
        self.spent_txs: List[str] = spent_txs
        self.get_spent_txs()

    @staticmethod
    def scriptPubKey(address: str) -> Script:
        """Convert base58 address to scriptPubKey"""
        h160 = decode_base58(address)
        script_pubkey = Script.p2pkh_script(h160)
        return script_pubkey

    def get_spent_txs(self):
        """Get transactions spent in memory pool by address"""
        for tx in self.memory_pool.MemoryPool.values():
            for tx_in in tx.tx_ins:
                self.spent_txs.append(tx_in.prev_tx.hex())

    def prepareTxIn(self):
        """Prepare transaction input"""
        tx_ins = []
        utxos = self.utxos.get_utxos_by_wallet(self.pubkey)

        fee_rate = self.memory_pool.get_fee_rate()
        size = 14 + 2 * (8 + len(self.scriptPubKey(self.toAccount).serialize()))

        for TxId in utxos:
            if self.Total > self.Amount + size * fee_rate:
                break
            if TxId not in self.spent_txs:
                tx = utxos[TxId]
                for index, tx_out in enumerate(tx.tx_outs):
                    if not tx_out:
                        continue
                    if tx_out.script_pubkey.cmds[2] == self.pubkey:
                        self.Total += tx_out.amount
                        prev_tx = bytes.fromhex(TxId)
                        tx_in = TxIn(prev_tx, index)
                        tx_ins.append(tx_in)
                        size += len(tx_in.serialize()) + 107
        self.isBalanceEnough = True
        self.fee = size * fee_rate
        if self.Total < self.Amount + self.fee:
            self.isBalanceEnough = False
        return tx_ins

    def prepareTxOut(self):
        """Prepare transaction output"""
        tx_outs = []
        pubkey = self.scriptPubKey(self.toAccount)
        tx_outs.append(TxOut(self.Amount, pubkey))
        change = self.Total - self.Amount - self.fee
        if change:
            tx_outs.append(TxOut(change, self.script_key))
        return tx_outs

    def prepareTransaction(self):
        """Prepare transaction"""
        tx_ins = self.prepareTxIn()
        if self.isBalanceEnough:
            tx_outs = self.prepareTxOut()
            self.TxObj = Tx(self.version, tx_ins, tx_outs, 0, int(time.time()))
            return self.TxObj
        return False

    def to_dict(self):
        """Convert transaction to dictionary"""
        return self.TxObj.to_dict()
