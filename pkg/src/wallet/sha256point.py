from pkg.src.utils import hash160, encode_base58_checksum
from pkg.src.wallet.constants import A, B, N, P
from pkg.src.wallet.point import Point
from pkg.src.wallet.sha256field import Sha256Field


class Sha256Point(Point):
    def __init__(self, x, y, a=None, b=None):
        a, b = Sha256Field(A), Sha256Field(B)
        if type(x) == int:
            super().__init__(x=Sha256Field(x), y=Sha256Field(y), a=a, b=b)
        else:
            super().__init__(x=x, y=y, a=a, b=b)  # <1>

    # end::source7[]

    def __repr__(self):
        if self.x is None:
            return "Sha256Point(infinity)"
        else:
            return "Sha256Point({}, {})".format(self.x, self.y)

    # tag::source8[]
    def __rmul__(self, coefficient):
        coef = coefficient % N  # <1>
        return super().__rmul__(coef)

    # end::source8[]

    # tag::source12[]
    def verify(self, z, sig):
        s_inv = pow(sig.s, N - 2, N)  # <1>
        u = z * s_inv % N  # <2>
        v = sig.r * s_inv % N  # <3>
        total = u * G + v * self  # <4>
        return total.x.num == sig.r  # <5>

    # end::source12[]
    def sec(self, compressed=True):
        """returns the binary version of the SEC format"""
        if compressed:
            if self.y.num % 2 == 0:
                return b"\x02" + self.x.num.to_bytes(32, "big")
            else:
                return b"\x03" + self.x.num.to_bytes(32, "big")
        else:
            return (
                    b"\x04"
                    + self.x.num.to_bytes(32, "big")
                    + self.y.num.to_bytes(32, "big")
            )

    def address(self, compressed=True, testnet=False):
        """Returns the address string"""
        h160 = hash160(self.sec(compressed))
        prefix = b"\x1c"
        return encode_base58_checksum(prefix + h160)

    @classmethod
    def parse(cls, sec_bin):
        """returns a Point object from a SEC binary (not hex)"""
        if sec_bin[0] == 4:  # <1>
            x = int.from_bytes(sec_bin[1:33], "big")
            y = int.from_bytes(sec_bin[33:65], "big")
            return Sha256Point(x=x, y=y)
        is_even = sec_bin[0] == 2  # <2>
        x = Sha256Field(int.from_bytes(sec_bin[1:], "big"))
        # right side of the equation y^2 = x^3 + 7
        alpha = x ** 3 + Sha256Field(B)
        # solve for left side
        beta = alpha.sqrt()  # <3>
        if beta.num % 2 == 0:  # <4>
            even_beta = beta
            odd_beta = Sha256Field(P - beta.num)
        else:
            even_beta = Sha256Field(P - beta.num)
            odd_beta = beta
        if is_even:
            return Sha256Point(x, even_beta)
        else:
            return Sha256Point(x, odd_beta)


G = Sha256Point(
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)
