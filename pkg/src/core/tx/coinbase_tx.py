import time

from pkg.src.core.script import Script
from pkg.src.core.tx.tx import Tx
from pkg.src.core.tx.tx_in import TxIn
from pkg.src.core.tx.tx_out import TxOut
from pkg.src.utils import int_to_little_endian, bytes_needed, decode_base58


class CoinbaseTx:
    """Miner reward transaction """
    ZERO_HASH: bytes = b"\0" * 32

    @staticmethod
    def REWARD(height: int):
        return int(5000000000 * 2**(-(height // 525600)) if height < 5256000 else 0)

    def __init__(self, block_height: int, miner_address: str):
        self.BlockHeightInLittleEndian: bytes = int_to_little_endian(block_height, bytes_needed(block_height))
        self.MINER_ADDRESS: str = miner_address

    def build(self, bloch_height: int) -> Tx:
        """Build coinbase transaction"""
        prev_tx = self.ZERO_HASH
        prev_index = 0xFFFFFFFF
        tx_ins = [TxIn(prev_tx, prev_index)]
        tx_ins[0].script_sig.cmds.append(self.BlockHeightInLittleEndian)

        tx_outs = []
        target_amount = self.REWARD(bloch_height)
        target_h160 = decode_base58(self.MINER_ADDRESS)
        target_script = Script.p2pkh_script(target_h160)
        tx_outs.append(TxOut(amount=target_amount, script_pubkey=target_script))
        coinbase_tx = Tx(1, tx_ins, tx_outs, 0, int(time.time()))
        coinbase_tx.TxId = coinbase_tx.id()

        return coinbase_tx
