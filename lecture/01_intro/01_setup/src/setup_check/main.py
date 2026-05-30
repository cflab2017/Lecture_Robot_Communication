"""
01. 실습 환경 준비 — 환경 자가진단 (setup_check)

Python / pymodbus / pyserial 설치와 _shared 공유 모듈 import 를 한 번에 점검한다.
이 스크립트가 "통과"로 끝나면 이후 모든 편의 실습을 진행할 수 있다.

실행:  python src/setup_check/main.py
"""
import os
import sys

# --- _shared 공유 라이브러리 경로 추가 (편 위치·깊이와 무관하게 상위에서 _shared 탐색) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "_shared")):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, "_shared"))

# cp949 콘솔에서도 한글/기호가 깨지거나 죽지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    ok = True
    print("=== 실습 환경 점검 ===")

    # 1) Python 버전 (3.10 이상 권장)
    major, minor = sys.version_info[:2]
    print(f"[1] Python {sys.version.split()[0]}", end="  ")
    if (major, minor) >= (3, 10):
        print("OK")
    else:
        print("주의: 3.10 이상 권장"); ok = False

    # 2) 의존성
    try:
        import pymodbus
        import serial
        print(f"[2] pymodbus {pymodbus.__version__} / pyserial {serial.__version__}  OK")
        if pymodbus.__version__ != "3.6.9":
            print("    주의: 본 강의는 pymodbus 3.6.9 기준입니다.")
    except ImportError as e:
        print(f"[2] 의존성 누락: {e}")
        print("    해결: cd lecture/_shared 후  python -m pip install -r requirements.txt")
        ok = False

    # 3) 공유 모듈 import + 변환 검증
    try:
        from word_tools import split_word, combine_word, ieee754_encode
        a = split_word(90000)               # A1 = 90.000°
        assert a == (24464, 1), a
        assert combine_word(*a) == 90000
        assert ieee754_encode(10.5) == 1093140480
        print(f"[3] _shared import OK: split_word(90000)={a}, "
              f"ieee754_encode(10.5)={ieee754_encode(10.5)}")
    except Exception as e:
        print(f"[3] 공유 모듈 점검 실패: {e}")
        ok = False

    print("-" * 30)
    print("환경 점검 통과 ✅" if ok else "환경 점검 실패 ❌ — 위 항목을 해결하세요")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
