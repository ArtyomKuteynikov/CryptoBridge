from socket import SocketIO
from typing import List

from pkg.src.wallet import OP_CODE_FUNCTION
from pkg.src.utils import encode_varint, read_varint, int_to_little_endian, little_endian_to_int


class Script:
    def __init__(self, cmds: List = None):
        self.cmds = cmds if cmds is not None else list()

    def __add__(self, other: 'Script') -> 'Script':
        return Script(self.cmds + other.cmds)

    def serialize(self) -> bytes:
        """Convert script into bytes"""
        result = b""
        for cmd in self.cmds:
            # if the cmd is an integer, it's an opcode
            if type(cmd) is int:
                # turn the cmd into a single byte integer using int_to_little_endian
                result += int_to_little_endian(cmd, 1)
            else:
                # otherwise, this is an element
                # get the length in bytes
                length = len(cmd)
                # for large lengths, we have to use a pushdata opcode
                if length < 75:
                    # turn the length into a single byte integer
                    result += int_to_little_endian(length, 1)
                elif 75 < length < 0x100:
                    # 76 is pushdata1
                    result += int_to_little_endian(76, 1)
                    result += int_to_little_endian(length, 1)
                elif 0x100 <= length <= 520:
                    # 77 is pushdata2
                    result += int_to_little_endian(77, 1)
                    result += int_to_little_endian(length, 2)
                else:
                    raise ValueError("Too long cmd")
                result += cmd
        # get the length of the whole thing
        total = len(result)
        # encode_varint the total length of the result and prepend
        return encode_varint(total) + result

    @classmethod
    def parse(cls, s: SocketIO) -> 'Script':
        """Parse script from bytes"""
        # get the length of the entire field
        length = read_varint(s)
        # initialize the cmds array
        cmds = []
        # initialize the number of bytes we've read to 0
        count = 0
        # loop until we've read length bytes
        while count < length:
            # get the current byte
            current = s.read(1)
            # increment the bytes we've read
            count += 1
            # convert the current byte to an integer
            current_byte = current[0]
            # if the current byte is between 1 and 75 inclusive
            if 1 <= current_byte <= 75:
                # we have a cmd set n to be the current byte
                n = current_byte
                # add the next n bytes as a cmd
                cmds.append(s.read(n))
                # increase the count by n
                count += n
            elif current_byte == 76:
                # op_pushdata1
                data_length = little_endian_to_int(s.read(1))
                cmds.append(s.read(data_length))
                count += data_length + 1
            elif current_byte == 77:
                # op_pushdata2
                data_length = little_endian_to_int(s.read(2))
                cmds.append(s.read(data_length))
                count += data_length + 2
            else:
                # we have an opcode. set the current byte to op_code
                op_code = current_byte
                # add the op_code to the list of cmds
                cmds.append(op_code)
        if count != length:
            raise SyntaxError('Parsing script failed')
        return cls(cmds)

    def evaluate(self, z: int) -> bool:
        """Check if script is valid"""
        cmds = self.cmds[:]
        stack = []
        while len(cmds) > 0:
            cmd = cmds.pop(0)
            if type(cmd) is int:
                operation = OP_CODE_FUNCTION[cmd]
                if cmd == 172:
                    if not operation(stack, z):
                        return False
                elif not operation(stack):
                    return False
            else:
                stack.append(cmd)
        return True

    @classmethod
    def p2pkh_script(cls, h160: bytes) -> 'Script':
        """Takes a hash160 and returns the p2pkh ScriptPubKey"""
        return Script([0x76, 0xA9, h160, 0x88, 0xAC])
