from pkg.src.utils import hash160
from .sha256point import Sha256Point
from .signature import Signature


class OPCode:

    @staticmethod
    def op_dup(stack):
        if len(stack) < 1:
            return False
        stack.append(stack[-1])

        return True

    @staticmethod
    def op_hash160(stack):
        if len(stack) < 1:
            return False
        element = stack.pop()
        h160 = hash160(element)
        stack.append(h160)
        return True

    @staticmethod
    def op_equal(stack):
        if len(stack) < 2:
            return False

        element1 = stack.pop()
        element2 = stack.pop()

        if element1 == element2:
            stack.append(1)
        else:
            stack.append(0)

        return True

    @staticmethod
    def op_verify(stack):
        if len(stack) < 1:
            return False
        element = stack.pop()

        if element == 0:
            return False

        return True

    @staticmethod
    def op_equal_verify(stack):
        return OPCode.op_equal(stack) and OPCode.op_verify(stack)

    @staticmethod
    def op_check_sig(stack, z):
        if len(stack) < 1:
            return False

        sec_pubkey = stack.pop()
        der_signature = stack.pop()[:-1]

        try:
            point = Sha256Point.parse(sec_pubkey)
            sig = Signature.parse(der_signature)
        except Exception as e:
            return False

        if point.verify(z, sig):
            stack.append(1)
            return True
        else:
            stack.append(0)
            return False
