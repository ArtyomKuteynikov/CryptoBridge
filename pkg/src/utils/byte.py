from math import log


class ByteUtils:
    """Utility class for working with bytes and integers."""

    @staticmethod
    def bytes_needed(number: int) -> int:
        """Calculates the minimum number of bytes needed to represent a number."""
        if number < 0:
            raise ValueError("Number must be non-negative")
        return 1 if number == 0 else int(log(number, 256)) + 1

    @staticmethod
    def int_to_little_endian(number: int, length: int) -> bytes:
        """Converts an integer to little-endian byte sequence of specified length."""
        return number.to_bytes(length, "little")

    @staticmethod
    def little_endian_to_int(byte_sequence: bytes) -> int:
        """Converts a little-endian byte sequence to an integer."""
        return int.from_bytes(byte_sequence, "little")
