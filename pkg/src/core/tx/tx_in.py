from socket import SocketIO

from pkg.src.core.script import Script
from pkg.src.utils import int_to_little_endian, little_endian_to_int


class TxIn:
    """
    Input transaction:
    Collect required amounts to transfer on another wallet
    """

    def __init__(self, prev_tx: bytes, prev_index: int, script_sig: Script | None = None, sequence: int = 0xFFFFFFFF):
        self.prev_tx: bytes = prev_tx
        self.prev_index: int = prev_index
        self.script_sig = script_sig or Script()
        self.sequence = sequence

    def serialize(self) -> bytes:
        """Convert TxIb into bytes"""
        result = self.prev_tx[::-1]
        result += int_to_little_endian(self.prev_index, 4)
        result += self.script_sig.serialize()
        result += int_to_little_endian(self.sequence, 4)
        return result

    @classmethod
    def parse(cls, s: SocketIO) -> 'TxIn':
        """Convert bytes into TxIn"""
        prev_tx = s.read(32)[::-1]
        prev_index = little_endian_to_int(s.read(4))
        script_sig = Script.parse(s)
        sequence = little_endian_to_int(s.read(4))
        return cls(prev_tx, prev_index, script_sig, sequence)
