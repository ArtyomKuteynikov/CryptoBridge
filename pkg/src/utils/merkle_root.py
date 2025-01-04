from typing import List

from pkg.src.utils.hash import HashUtils


class MerkleUtils:
    @staticmethod
    def merkle_parent_level(hashes: List[bytes]) -> List[bytes]:
        """Computes the parent level of a Merkle tree from a list of hashes."""
        if len(hashes) % 2 == 1:
            # If the number of hashes is odd, duplicate the last hash
            hashes.append(hashes[-1])

        parent_level = []
        for i in range(0, len(hashes), 2):
            parent = HashUtils.hash256(hashes[i] + hashes[i + 1])
            parent_level.append(parent)
        return parent_level

    @staticmethod
    def merkle_root(hashes: List[bytes]) -> bytes:
        """Computes the Merkle root of a list of hashes."""
        current_level = hashes
        while len(current_level) > 1:
            current_level = MerkleUtils.merkle_parent_level(current_level)
        return current_level[0]
