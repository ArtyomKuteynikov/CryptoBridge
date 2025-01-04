from typing import Tuple

from pkg.src.utils.byte import ByteUtils


class TargetUtils:
    MAX_TARGET = 0x0000ffff00000000000000000000000000000000000000000000000000000000

    AVERAGE_BLOCK_MINE_TIME = 60  # Calculate new Target to keep our Block mine time approx 20 seconds
    RESET_DIFFICULTY_AFTER_BLOCKS = 10  # Reset Block Difficulty after every 10 Blocks

    @staticmethod
    def target_to_bits(target: int) -> bytes:
        """Converts a target integer to its compact representation as bits."""
        raw_bytes = target.to_bytes(32, "big").lstrip(b"\x00")
        if raw_bytes[0] > 0x7F:
            exponent = len(raw_bytes) + 1
            coefficient = b"\x00" + raw_bytes[:2]
        else:
            exponent = len(raw_bytes)
            coefficient = raw_bytes[:3]
        return coefficient[::-1] + bytes([exponent])

    @staticmethod
    def bits_to_target(bits: bytes) -> int:
        """Converts bits (compact representation) to a target integer."""
        exponent = bits[-1]
        coefficient = ByteUtils.little_endian_to_int(bits[:-1])
        return coefficient * 256 ** (exponent - 3)

    @staticmethod
    def get_target_and_timestamp(block) -> Tuple[bytes, int]:
        bits = block.BlockHeader.bits
        timestamp = block.BlockHeader.timestamp
        return bits, timestamp

    def adjust_target(self, block, prev_block) -> int:
        bits, timestamp = self.get_target_and_timestamp(prev_block)
        _, last_timestamp = self.get_target_and_timestamp(block)
        last_target = self.bits_to_target(bits)
        average_block_mine_time = last_timestamp - timestamp
        time_ratio = average_block_mine_time / (self.AVERAGE_BLOCK_MINE_TIME * self.RESET_DIFFICULTY_AFTER_BLOCKS)
        new_target = int(format(int(last_target * time_ratio)))
        if new_target > self.MAX_TARGET:
            new_target = self.MAX_TARGET
        return new_target
