from socket import SocketIO


class RequestBlock:
    """Request blocks command"""
    command = b'requestBlock'

    def __init__(self, start_block: bytes, end_block: bytes = None):
        if start_block is None:
            raise RuntimeError("Starting Block cannot be None")

        self.startBlock: bytes = start_block
        self.endBlock: bytes = end_block if end_block is not None else b'\x00' * 32

    @classmethod
    def parse(cls, stream: SocketIO) -> 'RequestBlock':
        start_block = stream.read(4)
        return cls(start_block=start_block)

    def serialize(self) -> bytes:
        result = self.startBlock
        result += self.endBlock
        return result
