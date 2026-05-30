"""
정답 2 — 좌표 변환 왕복 검증

핵심 포인트:
- _shared 탐색 부트스트랩이 있어야 word_tools 를 import 할 수 있다.
- 좌표는 0.001 스케일이므로 ×1000 해서 정수 raw 로 만든 뒤 split_word 한다.
- split_word 는 부호 있는 16bit word 를 돌려준다. High word 가 음수일 수 있다.

흔한 실수:
- 부트스트랩 누락 -> ModuleNotFoundError: word_tools
- 복원 시 ÷1000 을 빠뜨려 1000배 큰 값이 나오는 것.
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

from word_tools import split_word, combine_word  # noqa: E402


def check(mm: float):
    raw = round(mm * 1000)
    low, high = split_word(raw)
    restored = combine_word(low, high) / 1000
    ok = abs(restored - mm) < 1e-9
    print(f"{mm:+.3f} mm -> Low={low}, High={high} -> 복원 {restored:g}  {'OK' if ok else 'FAIL'}")


def main():
    check(123.456)
    check(-123.456)


if __name__ == "__main__":
    main()
