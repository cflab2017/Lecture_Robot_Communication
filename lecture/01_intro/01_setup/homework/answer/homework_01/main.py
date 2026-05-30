"""
정답 1 — 의존성 자가진단

핵심 포인트:
- import 실패를 try/except ImportError 로 잡아 프로그램이 죽지 않게 한다.
- serial 모듈의 패키지 이름은 pyserial 이지만 import 이름은 serial 이다.

흔한 실수:
- `pip install serial` 로 다른(엉뚱한) 패키지를 까는 것. 반드시 `pyserial` 을 설치한다.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    print(f"Python {sys.version.split()[0]}")
    ready = True
    for import_name, label in (("pymodbus", "pymodbus"), ("serial", "pyserial")):
        try:
            mod = __import__(import_name)
            print(f"{label} {getattr(mod, '__version__', '?')}")
        except ImportError:
            print(f"{label} 없음 -> python -m pip install -r ../../_shared/requirements.txt")
            ready = False
    print("READY" if ready else "NOT READY")


if __name__ == "__main__":
    main()
