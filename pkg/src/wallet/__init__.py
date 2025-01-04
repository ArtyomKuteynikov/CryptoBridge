from .field_element import FieldElement
from .op import OPCode
from .point import Point
from .private_key import PrivateKey
from .sha256field import Sha256Field
from .sha256point import Sha256Point
from .signature import Signature

OP_CODE_FUNCTION = {118: OPCode.op_dup, 136: OPCode.op_equal_verify, 169: OPCode.op_hash160, 172: OPCode.op_check_sig}

__all__ = ["FieldElement", "PrivateKey", "Point", "Signature", "Sha256Field", "Sha256Point", "OP_CODE_FUNCTION"]
