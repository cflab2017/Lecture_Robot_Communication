"""
정답 2 — non-format(ASCII decimal) 인코딩/디코딩

핵심 포인트:
- non-format 은 시작/끝({ })·구분(,) 기호가 전혀 없고, 각 문자를 ASCII CODE
  (10진수) 1바이트로 해석한다. 즉 문자 1개 = 정수 1개.
- 인코딩은 ord(문자), 디코딩은 chr(코드) 로 1:1 대응된다.
- format 패킷이 "{65,66}" 처럼 보인다면, non-format 은 그냥 [65, 66] 바이트열이다.

흔한 실수:
- 숫자 문자열 "65" 를 정수 65 로 착각하는 것. non-format 에서 '6' 과 '5' 는
  각각 ord('6')=54, ord('5')=53 두 바이트다.
- ASCII 범위(0~127) 밖 문자를 1바이트로 가정하는 것(여기선 ASCII 만 다룬다).
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


def encode_nonformat(text: str) -> list:
    """문자열 -> ASCII CODE(10진수) 리스트. "AB" -> [65, 66]."""
    return [ord(ch) for ch in text]


def decode_nonformat(codes) -> str:
    """ASCII CODE(10진수) 리스트 -> 문자열. [65, 66] -> "AB"."""
    return "".join(chr(c) for c in codes)


def check(text: str):
    codes = encode_nonformat(text)
    restored = decode_nonformat(codes)
    ok = restored == text
    print(f"\"{text}\"  -> {codes}  -> \"{restored}\"  {'OK' if ok else 'FAIL'}")


def main():
    check("AB")
    check("123")          # 문자 '1','2','3' = 49,50,51 (정수 123 이 아님에 주의)
    check("OK")


if __name__ == "__main__":
    main()
