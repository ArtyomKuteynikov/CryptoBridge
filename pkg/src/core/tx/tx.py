from io import BytesIO
from socket import SocketIO
from typing import List

from pkg.src.wallet import PrivateKey
from pkg.src.core.script import Script
from pkg.src.core.tx.tx_in import TxIn
from pkg.src.core.tx.tx_out import TxOut
from pkg.src.utils import hash256, little_endian_to_int, read_varint, int_to_little_endian, bytes_needed, encode_varint


class Tx:
    """Transaction object"""
    command = b'newTxMemPool'

    def __init__(self, version: int, tx_ins: List[TxIn], tx_outs: List[TxOut], locktime: int, timestamp: int):
        self.version: int = version
        self.tx_ins: List[TxIn] = tx_ins
        self.tx_outs: List[TxOut | None] = tx_outs
        self.locktime: int = locktime
        self.sig_hash: int = 1
        self.timestamp: int = timestamp
        self.TxId: str = self.id()
        self.size: int = self.calculate_size()
        self.fee: int = 0

    def id(self) -> str:
        """Human-readable Tx id"""
        return self.hash().hex()

    def hash(self) -> bytes:
        """Binary Has of serialization"""
        return hash256(self.serialize())[::-1]

    @classmethod
    def parse(cls, s: SocketIO | BytesIO) -> 'Tx':
        """
        Takes a byte stream and parses the transaction at the start
        return a Tx object
        """
        version = little_endian_to_int(s.read(4))
        num_inputs = read_varint(s)
        inputs = []
        for _ in range(num_inputs):
            inputs.append(TxIn.parse(s))
        num_outputs = read_varint(s)
        outputs = []
        for _ in range(num_outputs):
            tx_out = TxOut.parse(s)
            if tx_out.amount:
                outputs.append(tx_out)
        lock_time = little_endian_to_int(s.read(4))
        timestamp = little_endian_to_int(s.read(4))
        return cls(version, inputs, outputs, lock_time, timestamp)

    def serialize(self) -> bytes:
        """Convert Tx object to bytes"""
        result = int_to_little_endian(self.version, 4)
        result += encode_varint(len(self.tx_ins))
        for tx_in in self.tx_ins:
            result += tx_in.serialize()
        result += encode_varint(len(self.tx_outs))
        for tx_out in self.tx_outs:
            result += tx_out.serialize()
        result += int_to_little_endian(self.locktime, 4)
        result += int_to_little_endian(self.timestamp, 4)
        return result

    def sigh_hash(self, input_index: int, script_pubkey: Script) -> int:
        """Create transaction hash so nobody can replace elements inside"""
        s = int_to_little_endian(self.version, 4)
        s += encode_varint(len(self.tx_ins))
        for i, tx_in in enumerate(self.tx_ins):
            if i == input_index:
                s += TxIn(tx_in.prev_tx, tx_in.prev_index, script_pubkey).serialize()
            else:
                s += TxIn(tx_in.prev_tx, tx_in.prev_index).serialize()
        s += encode_varint(len(self.tx_outs))
        for tx_out in self.tx_outs:
            s += tx_out.serialize()
        s += int_to_little_endian(self.locktime, 4)
        s += int_to_little_endian(self.timestamp, 4)
        s += int_to_little_endian(self.sig_hash, 4)
        h256 = hash256(s)
        return int.from_bytes(h256, "big")

    def sign_input(self, input_index: int, private_key: PrivateKey, script_pubkey: Script):
        """Sign tx_in with the given input_index using private key"""
        z = self.sigh_hash(input_index, script_pubkey)
        der = private_key.sign(z).der()
        sig = der + self.sig_hash.to_bytes(1, "big")
        sec = private_key.point.sec()
        self.tx_ins[input_index].script_sig = Script([sig, sec])

    def verify_input(self, input_index: int, script_pubkey: Script) -> bool:
        """Check if tx_in with input_index is correctly signed"""
        tx_in = self.tx_ins[input_index]
        z = self.sigh_hash(input_index, script_pubkey)
        combined = tx_in.script_sig + script_pubkey
        return combined.evaluate(z)

    def is_coinbase(self) -> bool:
        """
        Check that there us exactly 1 input grab the first input and check if the prev_tx is b'\x00' * 32 check that the first input prev_index is 0xffffffff
        """
        if len(self.tx_ins) != 1:
            return False
        first_input = self.tx_ins[0]
        if first_input.prev_tx != b"\x00" * 32:
            return False
        if first_input.prev_index != 0xFFFFFFFF:
            return False
        return True

    @classmethod
    def to_obj(cls, item: dict) -> 'Tx':
        """Convert transaction in dict format to Tx object"""
        tx_ins = []
        tx_outs = []
        cmds = []
        version = item['version']
        locktime = item['locktime']
        timestamp = item['timestamp']
        for tx_in in item['tx_ins']:
            for cmd in tx_in['script_sig']['cmds']:
                if tx_in['prev_tx'] == "0000000000000000000000000000000000000000000000000000000000000000":
                    cmds.append(int_to_little_endian(int(cmd), bytes_needed(int(cmd))))
                else:
                    if type(cmd) is int:
                        cmds.append(cmd)
                    else:
                        cmds.append(bytes.fromhex(cmd))
            tx_ins.append(TxIn(bytes.fromhex(tx_in['prev_tx']), tx_in['prev_index'], Script(cmds)))
            cmds = []
        cmds_out = []
        for tx_out in item['tx_outs']:
            if not tx_out:
                tx_outs.append(None)
                continue
            for cmd in tx_out['script_pubkey']['cmds']:
                if type(cmd) is int:
                    cmds_out.append(cmd)
                else:
                    cmds_out.append(bytes.fromhex(cmd))
            tx_outs.append(TxOut(tx_out['amount'], Script(cmds_out)))
            cmds_out = []
        return cls(version, tx_ins, tx_outs, locktime, timestamp)

    def to_dict(self) -> dict:
        """
        Convert Transaction
        Convert prev_tx Hash in hex from bytes
        Convert BlockHeight in hex which is stored in Script signature
        """
        tx_dict = self.__dict__
        for tx_index, tx_in in enumerate(tx_dict['tx_ins']):
            if self.is_coinbase():
                tx_in.script_sig.cmds[0] = little_endian_to_int(
                    tx_in.script_sig.cmds[0]
                )
            tx_in.prev_tx = tx_in.prev_tx.hex()
            for index, cmd in enumerate(tx_in.script_sig.cmds):
                if isinstance(cmd, bytes):
                    tx_in.script_sig.cmds[index] = cmd.hex()
            tx_in.script_sig = tx_in.script_sig.__dict__
            tx_dict['tx_ins'][tx_index] = tx_in.__dict__
        for index, tx_out in enumerate(tx_dict['tx_outs']):
            if not tx_out:
                tx_dict['tx_outs'][index] = None
                continue
            tx_out.script_pubkey.cmds[2] = tx_out.script_pubkey.cmds[2].hex()
            tx_out.script_pubkey = tx_out.script_pubkey.__dict__
            tx_dict['tx_outs'][index] = tx_out.__dict__
        return tx_dict

    def calculate_fee(self, utxos) -> float:
        """Calculate transaction fee amount (diff btw amount of inputs and outputs)"""
        input_amount, output_amount = 0, 0
        for tx_in in self.tx_ins:
            if tx_in.prev_tx.hex() in utxos:
                prev_tx = utxos.get(tx_in.prev_tx.hex()).tx_outs[tx_in.prev_index]
                if prev_tx:
                    input_amount += prev_tx.amount
        for tx_out in self.tx_outs:
            output_amount += tx_out.amount
        self.fee = input_amount - output_amount
        return self.fee

    def calculate_size(self):
        """Get size of serialised tx"""
        return len(self.serialize())
