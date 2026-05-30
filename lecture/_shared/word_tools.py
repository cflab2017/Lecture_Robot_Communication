"""
word_tools.py  —  HIWIN 로봇 Modbus 데이터 변환 실습 도구

매뉴얼 Appendix II(32bit 분할 저장)와 5.4.4(SWAP_WORD / IEEE754) 내용을
파이썬으로 직접 확인해 보는 학습용 모듈입니다. pymodbus 가 필요 없습니다.

실행:
    python word_tools.py          # 데모(매뉴얼 예제 검증)
    python word_tools.py 90.83    # 임의 실수 값으로 분할/복원 확인
"""
import struct
import sys


# ---------------------------------------------------------------------------
# 1) 32bit 값 ↔ Low/High word 분할  (매뉴얼 Appendix II, p.131~133)
#    로봇은 16bit를 초과하는 값(좌표, 속도 등)을 두 레지스터에 나눠 저장한다.
#    각 word 는 부호 있는 16bit(-32768~32767) 이다.
# ---------------------------------------------------------------------------
def split_word(value: int):
    """부호 있는 정수 -> (low_word, high_word).  둘 다 signed 16bit.

    >>> split_word(90830)      # A1 = 90.830° (= 90.83 * 1000)
    (25294, 1)
    >>> split_word(300000)     # X = +300.000 mm
    (-27680, 4)
    >>> split_word(-300000)    # X = -300.000 mm
    (27680, -5)
    """
    high = value // 65536            # 몫 (음수면 내림 → 매뉴얼 규칙과 일치)
    rem = value % 65536              # 나머지: 항상 0~65535
    low = rem - 65536 if rem > 32767 else rem   # signed 16bit 로 표현
    return low, high


def combine_word(low: int, high: int) -> int:
    """(low_word, high_word) -> 원래 부호 있는 정수.

    >>> combine_word(25294, 1)
    90830
    >>> combine_word(-6742, -7)    # X = -399.958 mm (매뉴얼 예제)
    -399958
    """
    return high * 65536 + (low & 0xFFFF)   # high는 부호 유지, low는 unsigned 취급


def to_engineering(low: int, high: int, scale: float = 0.001) -> float:
    """Low/High word 를 실제 공학 값으로. (좌표/각도는 scale=0.001)"""
    return combine_word(low, high) * scale


# ---------------------------------------------------------------------------
# 2) SWAP_WORD  (매뉴얼 5.4.4.1, p.102)
#    32bit 값의 상위/하위 word 자리를 교환한다. (장비별 byte order 차이 보정)
# ---------------------------------------------------------------------------
def swap_word(v: int) -> int:
    """High word ↔ Low word 교환.

    >>> swap_word(10)        # 0x0000000A -> 0x000A0000
    655360
    """
    v &= 0xFFFFFFFF
    return ((v & 0xFFFF) << 16) | ((v >> 16) & 0xFFFF)


# ---------------------------------------------------------------------------
# 3) IEEE754 단정도(single precision) 변환  (매뉴얼 5.4.4.2 / 5.4.4.3, p.104~105)
#    Modbus 는 실수를 직접 전송하지 못하므로 32bit 정수로 인코딩해 주고받는다.
# ---------------------------------------------------------------------------
def ieee754_encode(f: float) -> int:
    """실수 -> 32bit 정수(IEEE754 single).

    >>> ieee754_encode(10.5)
    1093140480
    """
    return struct.unpack(">I", struct.pack(">f", f))[0]


def ieee754_decode(i: int) -> float:
    """32bit 정수(IEEE754 single) -> 실수.

    >>> ieee754_decode(1093140480)
    10.5
    """
    return struct.unpack(">f", struct.pack(">I", i & 0xFFFFFFFF))[0]


def reg_to_int32(reg_low: int, reg_high: int) -> int:
    """레지스터 2개(unsigned 16bit) -> unsigned 32bit. IEEE754 디코딩 전처리용."""
    return ((reg_high & 0xFFFF) << 16) | (reg_low & 0xFFFF)


# ---------------------------------------------------------------------------
# 데모
# ---------------------------------------------------------------------------
def _demo():
    print("=== 32bit 분할/복원 (Appendix II) ===")
    for eng in (90.830, 300.000, -399.958):
        raw = round(eng * 1000)
        low, high = split_word(raw)
        back = to_engineering(low, high)
        print(f"  {eng:>10.3f}  ->  raw={raw:>8}  Low={low:>7}  High={high:>3}"
              f"  ->  복원={back:>10.3f}  {'OK' if abs(back-eng) < 1e-6 else 'FAIL'}")

    print("\n=== SWAP_WORD (5.4.4.1) ===")
    print(f"  swap_word(10)        = {swap_word(10)}        (기대 655360)")

    print("\n=== IEEE754 (5.4.4.2/3) ===")
    print(f"  ieee754_encode(10.5) = {ieee754_encode(10.5)}  (기대 1093140480)")
    print(f"  ieee754_decode(...)  = {ieee754_decode(1093140480)}        (기대 10.5)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        val = float(sys.argv[1])
        raw = round(val * 1000)
        low, high = split_word(raw)
        print(f"입력 {val}  (×1000 = {raw})")
        print(f"  Low word  = {low}   (0x{low & 0xFFFF:04X})")
        print(f"  High word = {high}  (0x{high & 0xFFFF:04X})")
        print(f"  복원      = {to_engineering(low, high)}")
        print(f"  IEEE754   = {ieee754_encode(val)}")
    else:
        _demo()
