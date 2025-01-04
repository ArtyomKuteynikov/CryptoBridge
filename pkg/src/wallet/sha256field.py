from pkg.src.wallet.constants import P
from pkg.src.wallet.field_element import FieldElement


class Sha256Field(FieldElement):
    def __init__(self, num, prime=None):
        super().__init__(num=num, prime=P)

    def __repr__(self):
        return "{:x}".format(self.num).zfill(64)

    def sqrt(self):
        return self ** ((P + 1) // 4)
