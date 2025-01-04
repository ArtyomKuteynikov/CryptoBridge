import hashlib

from pkg.src.utils.hash import HashUtils


class Base58Utils:
    """Utility class for Base58 encoding and decoding."""
    BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    @staticmethod
    def encode(data: bytes) -> str:
        """Encodes bytes into a Base58 string."""
        num = int.from_bytes(data, 'big')
        result = ''
        while num > 0:
            num, mod = divmod(num, 58)
            result = Base58Utils.BASE58_ALPHABET[mod] + result
        return result

    @staticmethod
    def decode(data: str) -> bytes:
        """Decodes a Base58 string back into bytes."""
        num = 0
        for char in data:
            num = num * 58 + Base58Utils.BASE58_ALPHABET.index(char)
        combined = num.to_bytes(25, "big")
        checksum = combined[-4:]
        if HashUtils.hash256(combined[:-4])[:4] != checksum:
            raise ValueError("Invalid address: checksum mismatch.")
        return combined[1:-4]

    @staticmethod
    def encode_checksum(b: bytes) -> str:
        """Encodes a Base58 string into a Base58 checksum."""
        return Base58Utils.encode(b + (hashlib.sha256(hashlib.sha256(b).digest()).digest())[:4])
