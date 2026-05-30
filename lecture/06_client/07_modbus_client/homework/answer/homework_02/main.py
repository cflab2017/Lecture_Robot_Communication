"""
정답 2 — IEEE754 왕복 변환 / SWAP_WORD 검증

핵심 포인트:
- Modbus 레지스터는 16bit 정수만 실어 나른다. 실수(부동소수점)는 직접 못 보내므로
  전송 전 IEEE754_ENCODE(실수->32bit 정수), 수신 후 IEEE754_DECODE(정수->실수) 한다.
- 장비 간 High/Low word 순서가 반대면 SWAP_WORD 로 자리를 교환해 보정한다.
- pymodbus 없이 _shared/word_tools.py 만으로 손계산을 검증한다.

검증값(매뉴얼 5.4.4):
- ieee754_encode(10.5) = 1093140480, ieee754_decode(1093140480) = 10.5
- swap_word(10) = 655360 (0x0000000A -> 0x000A0000)

흔한 실수:
- 실수를 레지스터에 그대로 쓰려다 깨지는 것. 반드시 IEEE754 인코딩 후 전송한다.
- 부트스트랩 누락 -> ModuleNotFoundError: word_tools
"""
import os
import sys

# _shared 공유 라이브러리 경로 추가 (깊이 무관하게 상위에서 _shared 탐색)
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "_shared")):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, "_shared"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from word_tools import ieee754_encode, ieee754_decode, swap_word  # noqa: E402


def roundtrip(value):
    """실수 -> 정수(encode) -> 실수(decode) 왕복 검증."""
    enc = ieee754_encode(value)
    dec = ieee754_decode(enc)
    ok = abs(dec - value) < 1e-6
    print(f"{value:>8} -> encode -> {enc:>12} -> decode -> {dec:<8g}  {'OK' if ok else 'FAIL'}")


def check_swap(v, expect):
    s = swap_word(v)
    ok = s == expect
    print(f"swap_word({v}) = {s}  (기대 {expect})  {'OK' if ok else 'FAIL'}")


def main():
    print("=== IEEE754 왕복 변환 (실수 -> 정수 -> 실수) ===")
    roundtrip(10.5)     # 1093140480
    roundtrip(50.0)     # 1112014848
    roundtrip(-12.25)

    print("\n=== SWAP_WORD (High/Low word 교환) ===")
    check_swap(10, 655360)            # 0x0000000A -> 0x000A0000
    check_swap(65535, 4294901760)     # 0x0000FFFF -> 0xFFFF0000

    print("\n=== 응용: 실수 좌표를 byte order 반대 장비로 보내는 시나리오 ===")
    coord = 10.5
    enc = ieee754_encode(coord)              # 전송 전 인코딩
    swapped = swap_word(enc)                 # 상대 장비 word 순서 반대 -> 보정
    restored = ieee754_decode(swap_word(swapped))  # 받은 쪽: 되돌린 뒤 디코딩
    ok = abs(restored - coord) < 1e-6
    print(f"{coord} -> encode {enc} -> swap {swapped} -> swap-back -> decode {restored}  "
          f"{'OK' if ok else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
