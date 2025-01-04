from io import BytesIO

from pkg.src.utils import little_endian_to_int


class FinishedSending:
    """Finish sending data server message"""
    command = b'Finished'
    FINISHED_SENDING = b'\x0a\x11\x09\x07'

    @classmethod
    def parse(cls, s: BytesIO) -> int | None:
        """Parse finish message"""
        magic = s.read(4)
        param = s.read(4)

        if magic == cls.FINISHED_SENDING:
            if param:
                return little_endian_to_int(param)

    def serialize(self, param: bytes | None = None) -> bytes:
        """Create finish message"""
        result = self.FINISHED_SENDING
        if param is not None:
            result += param
        return result
