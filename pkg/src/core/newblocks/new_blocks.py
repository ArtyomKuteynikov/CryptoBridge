from multiprocessing.managers import DictProxy
from typing import Dict, List

from pkg.src.core.secondarychain import SecondaryChain
from pkg.src.core.tx import CoinbaseTx, Tx
from pkg.src.core.utxos import UTXOs
from pkg.src.core.block import Block
from pkg.src.utils import merkle_root


class NewBlocks:
    def __init__(self, new_blocks: DictProxy):
        self.NewBlocks: DictProxy[str, Block] = new_blocks

    def add(self, block: Block):
        tx_ids = list()
        for tx in block.Txs:
            tx_ids.append(tx.hash())
        if block.BlockHeader.merkleRoot != merkle_root(tx_ids)[::-1]:
            raise Exception("Merkle root mismatch")
        if not block.BlockHeader.check_pow():
            raise Exception("PoW mismatch")

        self.NewBlocks[block.BlockHeader.generateBlockHash()] = block

    def check_block(self, block: Block, utxos: UTXOs, db, sec_chain: SecondaryChain):
        fee_amount = 0
        mined_amount = 0
        secondary_utxos = self.sec_chain_txs(block, utxos, db, sec_chain)
        for tx in block.Txs:
            if tx.is_coinbase():
                mined_amount = tx.tx_outs[0].amount
            else:
                input_amount = 0
                output_amount = 0
                for index, tx_in in enumerate(tx.tx_ins):
                    prev_tx = secondary_utxos.get(tx_in.prev_tx.hex())
                    if not prev_tx:
                        raise Exception(f"Incorrect input {tx_in.prev_tx.hex()}")
                    if not prev_tx.tx_outs[tx_in.prev_index]:
                        raise Exception("Double spending")
                    script = prev_tx.tx_outs[tx_in.prev_index].script_pubkey
                    if not tx.verify_input(index, script):
                        raise Exception("Verification error")
                    input_amount += prev_tx.tx_outs[tx_in.prev_index].amount
                for tx_out in tx.tx_outs:
                    output_amount += tx_out.amount
                fee_amount += input_amount - output_amount
        if mined_amount - fee_amount > CoinbaseTx.REWARD(block.Height):
            raise Exception("Too big mined amount")

    @staticmethod
    def sec_chain_txs(block: Block, utxos: UTXOs, db, sec_chain: SecondaryChain) -> Dict[str, Tx]:
        chain = list()
        prev_blockhash = block.BlockHeader.prevBlockHash
        for _ in sec_chain:
            if prev_blockhash in sec_chain:
                prev_block = sec_chain.get(prev_blockhash)
                chain.append(prev_block)
                prev_blockhash = prev_block.BlockHeader.prevBlockHash.hex()
        secondary_utxos = utxos.to_dict()

        """Renewing UTXOs to last valid block"""
        for block in [block] + chain:
            chain_block = db.get_block(block.Height)
            if chain_block:
                for tx in chain_block.Txs:
                    try:
                        del secondary_utxos[tx.id()]
                    except KeyError:
                        pass
                    if tx.is_coinbase():
                        continue
                    for tx_in in tx.tx_ins:
                        prev_tx = db.find_transaction(tx_in.prev_tx.hex())
                        if tx_in.prev_tx.hex() in secondary_utxos:
                            tx = secondary_utxos[tx_in.prev_tx.hex()]
                            tx.tx_outs[tx_in.prev_index] = prev_tx.tx_outs[tx_in.prev_index]
                            secondary_utxos[prev_tx.TxId] = tx
                        else:
                            secondary_utxos[prev_tx.TxId] = prev_tx

        """Updating UTXOs to secondary chain transactions"""
        for block in chain[::-1]:
            for tx in block.Txs:
                secondary_utxos[tx.id()] = tx
                if tx.is_coinbase():
                    continue
                for tx_in in tx.tx_ins:
                    try:
                        if len(secondary_utxos[tx_in.prev_tx.hex()].tx_outs) - secondary_utxos[tx_in.prev_tx.hex()].tx_outs.count(None) > 1:
                            tx = secondary_utxos[tx_in.prev_tx.hex()]
                            tx.tx_outs[tx_in.prev_index] = None
                            secondary_utxos[tx_in.prev_tx.hex()] = tx
                        else:
                            del secondary_utxos[tx_in.prev_tx.hex()]
                    except (KeyError, IndexError):
                        pass
        return secondary_utxos

    def to_dict(self) -> Dict[str, Block]:
        return dict(self.NewBlocks)

    def remove(self, blockhash: str):
        try:
            del self.NewBlocks[blockhash]
        except KeyError:
            pass

    def delete(self, blocks: List[str]):
        for block in blocks:
            self.remove(block)

    def __bool__(self):
        return bool(self.NewBlocks)
