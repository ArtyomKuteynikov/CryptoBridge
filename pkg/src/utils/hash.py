from hashlib import sha256

from Crypto.Hash import RIPEMD160


class HashUtils:
    """Utility class for hash operations."""

    @staticmethod
    def hash256(data: bytes) -> bytes:
        """Applies SHA256 twice to the input data."""
        return sha256(sha256(data).digest()).digest()

    @staticmethod
    def hash160(data: bytes) -> bytes:
        """Applies SHA256 followed by RIPEMD160."""
        return RIPEMD160.new(sha256(data).digest()).digest()
