from io import BytesIO


class Handshake:
    """Command to sign up new node in blockchain"""

    command = b'handshake'
    HANDSHAKE = b'\x05\xf5\xe1\x00'

    @classmethod
    def parse(cls, s: BytesIO) -> bool:
        """Parse handshake message"""
        magic = s.read(4)

        if magic == cls.HANDSHAKE:
            return True
        return False

    def serialize(self) -> bytes:
        """Create handshake message"""
        result = self.HANDSHAKE
        return result
