from io import BytesIO
from socket import SocketIO
from typing import List

from pkg.src.utils import read_varint, little_endian_to_int, encode_varint, int_to_little_endian


class NodeList:
    """Nodes list utils"""
    command = b'nodelist'

    def __init__(self, nodes: List[str] | None = None):
        self.nodes: List[str] = nodes or list()

    @classmethod
    def parse(cls, s: SocketIO | BytesIO) -> List[str]:
        """Parse incoming nodes"""
        nodes = list()
        length = read_varint(s)
        for _ in range(length):
            node_len = little_endian_to_int(s.read(1))
            node = bytes.decode(s.read(node_len))
            nodes.append(node)
        return nodes

    def serialize(self) -> bytes:
        """Serialise nodes for sending"""
        result = encode_varint(len(self.nodes))
        for node in self.nodes:
            result += int_to_little_endian(len(bytes(node, 'utf-8')), 1)
            result += bytes(node, 'utf-8')
        return result
