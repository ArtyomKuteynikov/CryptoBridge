from .base58 import Base58Utils
from .bits import TargetUtils
from .byte import ByteUtils
from .hash import HashUtils
from .merkle_root import MerkleUtils
from .varint import VarIntUtils

__all__ = [
    "HashUtils",
    "ByteUtils",
    "Base58Utils",
    "VarIntUtils",
    "MerkleUtils",
    "TargetUtils",
    "hash256",
    "hash160",
    "bytes_needed",
    "int_to_little_endian",
    "little_endian_to_int",
    "encode_varint",
    "read_varint",
    "encode_base58",
    "decode_base58",
    "encode_base58_checksum",
    "merkle_root",
    "target_to_bits",
    "bits_to_target",
    "get_target_and_timestamp",
    "adjust_target",
    "RESET_DIFFICULTY_AFTER_BLOCKS"
]

hash256 = HashUtils.hash256
hash160 = HashUtils.hash160

bytes_needed = ByteUtils.bytes_needed
int_to_little_endian = ByteUtils.int_to_little_endian
little_endian_to_int = ByteUtils.little_endian_to_int

encode_base58 = Base58Utils.encode
decode_base58 = Base58Utils.decode
encode_base58_checksum = Base58Utils.encode_checksum

encode_varint = VarIntUtils.encode
read_varint = VarIntUtils.decode

merkle_root = MerkleUtils.merkle_root

target_to_bits = TargetUtils.target_to_bits
bits_to_target = TargetUtils.bits_to_target
get_target_and_timestamp = TargetUtils.get_target_and_timestamp
adjust_target = TargetUtils().adjust_target
RESET_DIFFICULTY_AFTER_BLOCKS = TargetUtils.RESET_DIFFICULTY_AFTER_BLOCKS
