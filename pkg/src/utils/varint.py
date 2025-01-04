from socket import SocketIO

from pkg.src.utils.byte import ByteUtils


class VarIntUtils:
    """Utility class for encoding and decoding VarInt."""

    @staticmethod
    def encode(number: int) -> bytes:
        """Encodes an integer into a variable-length format."""
        if number < 0xfd:
            return bytes([number])
        elif number < 0x10000:
            return b'\xfd' + ByteUtils.int_to_little_endian(number, 2)
        elif number < 0x100000000:
            return b'\xfe' + ByteUtils.int_to_little_endian(number, 4)
        elif number < 0x10000000000000000:
            return b'\xff' + ByteUtils.int_to_little_endian(number, 8)
        raise ValueError(f"Integer too large: {number}")

    @staticmethod
    def decode(stream: SocketIO | bytes) -> int:
        """Reads a variable-length integer from a stream."""
        prefix = stream.read(1)[0]
        if prefix == 0xfd:
            return ByteUtils.little_endian_to_int(stream.read(2))
        elif prefix == 0xfe:
            return ByteUtils.little_endian_to_int(stream.read(4))
        elif prefix == 0xff:
            return ByteUtils.little_endian_to_int(stream.read(8))
        return prefix
