from socket import SocketIO

from pkg.src.core.script import Script
from pkg.src.utils import int_to_little_endian, little_endian_to_int


class TxOut:
    """
    Output transaction:
    Transfer
    """

    def __init__(self, amount: int, script_pubkey: Script):
        self.amount: int = amount
        self.script_pubkey: Script = script_pubkey

    def serialize(self) -> bytes:
        """Serialise TxOut into bytes"""
        result = int_to_little_endian(self.amount, 8)
        result += self.script_pubkey.serialize()
        return result

    @classmethod
    def parse(cls, s: SocketIO) -> 'TxOut':
        """Parse TxOut object from socket stream"""
        amount = little_endian_to_int(s.read(8))
        script_pubkey = Script.parse(s)
        return cls(amount, script_pubkey)
