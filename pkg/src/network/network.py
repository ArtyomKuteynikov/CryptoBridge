from io import BytesIO, BufferedReader
from socket import SocketIO

from pkg.src.utils import hash256, little_endian_to_int, int_to_little_endian


class NetworkEnvelope:
    """Data converter to and from bytestring format for network envelopes."""
    NETWORK_MAGIC = b'\xf9\xbe\xb4\xd9'

    def __init__(self, command: bytes, payload: bytes):
        self.command: bytes = command
        self.payload: bytes = payload

    @classmethod
    def parse(cls, s: SocketIO | BufferedReader) -> 'NetworkEnvelope':
        """Parse data from stream"""
        magic = s.read(4)
        if magic != cls.NETWORK_MAGIC:
            raise RuntimeError(f"Magic is not right {magic.hex()} vs {cls.NETWORK_MAGIC.hex()}")
        command = s.read(12)
        command = command.strip(b'\x00')
        payload_len = little_endian_to_int(s.read(4))
        checksum = s.read(4)
        payload = s.read(payload_len)
        calculated_checksum = hash256(payload)[:4]
        if calculated_checksum != checksum:
            raise IOError("Checksum does not match")
        return cls(command, payload)

    def serialize(self) -> bytes:
        """Convert message to bytes for sending"""
        result = self.NETWORK_MAGIC
        result += self.command + b'\x00' * (12 - len(self.command))
        result += int_to_little_endian(len(self.payload), 4)
        result += hash256(self.payload)[:4]
        result += self.payload
        return result

    def stream(self) -> BytesIO:
        """Convert payload to bytes for streaming"""
        return BytesIO(self.payload)
