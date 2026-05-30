"""
정답 1 — 정수 리스트 패킷 프레이밍/역파싱

핵심 포인트:
- HIWIN 포맷은 값을 콤마 , 로 잇고, 전체를 중괄호 { } 로 감싼다.
- 역파싱은 먼저 { } 를 벗긴 뒤 , 로 split 하고 각 토큰을 int 로 변환한다.
- 음수·여러 자리 정수도 같은 규칙으로 왕복(round-trip)된다.

흔한 실수:
- { } 를 벗기지 않고 split 해 첫/마지막 토큰에 중괄호가 붙는 것.
- 파싱 결과를 문자열로 둔 채 원본 정수 리스트와 == 비교해 항상 다르게 나오는 것.
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


def frame(values) -> str:
    """정수 리스트 -> "{a,b,c}" 패킷 문자열 (CWRITE 가 보낼 모양)."""
    return "{" + ",".join(str(v) for v in values) + "}"


def unframe(packet: str) -> list:
    """"{a,b,c}" 패킷 문자열 -> 정수 리스트 (CREAD 가 받아 파싱한 결과)."""
    body = packet.strip().strip("{}")
    if not body:
        return []
    return [int(tok) for tok in body.split(",")]


def check(values):
    packet = frame(values)
    restored = unframe(packet)
    ok = restored == values
    print(f"{values}  -> \"{packet}\"  -> {restored}  {'OK' if ok else 'FAIL'}")


def main():
    check([123, 456])
    check([90000, -45100, 30])
    check([7])


if __name__ == "__main__":
    main()
