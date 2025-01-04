from socket import SocketIO

from pkg.src.utils import hash256, bits_to_target, little_endian_to_int, int_to_little_endian


class BlockHeader:
    def __init__(
            self,
            version: int,
            prev_block_hash: bytes,
            merkle_root: bytes,
            timestamp: int,
            bits: bytes,
            nonce: int = None
    ):
        self.version: int = version
        self.prevBlockHash: bytes = prev_block_hash
        self.merkleRoot: bytes = merkle_root
        self.timestamp: int = timestamp
        self.bits: bytes = bits
        self.nonce: int = nonce
        self.blockHash: bytes = b""

    @classmethod
    def parse(cls, s: SocketIO) -> 'BlockHeader':
        """Parse BlockHeader from bytes."""
        version = little_endian_to_int(s.read(4))
        prev_block_hash = s.read(32)[::-1]
        merkle_root = s.read(32)[::-1]
        timestamp = little_endian_to_int(s.read(4))
        bits = s.read(4)
        nonce = little_endian_to_int(s.read(4))
        return cls(version, prev_block_hash, merkle_root, timestamp, bits, nonce)

    def serialize(self) -> bytes:
        """Serialize BlockHeader into bytes."""
        result = int_to_little_endian(self.version, 4)
        result += self.prevBlockHash[::-1]
        result += self.merkleRoot[::-1]
        result += int_to_little_endian(self.timestamp, 4)
        result += self.bits
        result += int_to_little_endian(self.nonce, 4)
        return result

    def mine(self, target: int, new_block_available) -> bool:
        """Find a nonce value to Block that will satisfy with PoW rule"""
        self.blockHash = target + 1
        while self.blockHash > target:
            if new_block_available:
                return True
            self.blockHash = little_endian_to_int(hash256(self.serialize()))
            self.nonce += 1
        self.blockHash = int_to_little_endian(self.blockHash, 32).hex()[::-1]
        self.nonce -= 1

    def check_pow(self) -> bool:
        """Check if the block hash meet PoW rule"""
        sha = hash256(self.serialize())
        proof = little_endian_to_int(sha)
        return proof < bits_to_target(self.bits)

    def generateBlockHash(self) -> str:
        """Generate a hash of the block."""
        sha = hash256(self.serialize())
        proof = little_endian_to_int(sha)
        return int_to_little_endian(proof, 32).hex()[::-1]

    def to_dict(self) -> dict:
        """Converts the BlockHeader object to a dictionary."""
        dt = self.__dict__
        dt['blockHash'] = self.generateBlockHash()
        dt['prevBlockHash'] = self.prevBlockHash.hex()
        dt['merkleRoot'] = self.merkleRoot.hex()
        dt['bits'] = self.bits.hex()
        return dt
