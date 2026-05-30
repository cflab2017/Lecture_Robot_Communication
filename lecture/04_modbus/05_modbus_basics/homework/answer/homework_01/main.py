"""
정답 1 — Holding Register 읽기 → 쓰기 → 재확인

핵심 포인트:
- Holding Register(주소 100, 속도 설정값)는 R/W 권한이라 마스터가 쓸 수 있다.
- 쓰기(write_holding, Function Code 06) 직후 다시 읽어(read_holding, FC03)
  값이 실제로 반영됐는지 "쓰고-되읽어-확인" 하는 습관이 중요하다.
- read_* 계열은 항상 '리스트'를 돌려준다. 단일 값은 [0] 인덱스로 꺼낸다.

흔한 실수:
- 슬레이브를 먼저 띄우지 않아 ConnectionError 가 나는 것.
- write 후 재확인을 생략해 반영 여부를 확인하지 않는 것.
- read_holding(100, 1) 의 반환값 [50] 을 정수 50 과 직접 비교하는 것
  (리스트와 정수는 같지 않다 → [0] 으로 꺼내서 비교).

실행:
    # 터미널 1: python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1
    # 터미널 2:
    python homework_01/main.py --port 1502
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

import argparse  # noqa: E402

from modbus_master import RobotMaster  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1502)
    ap.add_argument("--unit", type=int, default=1)
    args = ap.parse_args()

    addr, new_value = 100, 75  # 속도 설정값을 75% 로 변경

    with RobotMaster(args.host, args.port, args.unit) as m:
        before = m.read_holding(addr, 1)[0]
        print(f"쓰기 전  read_holding({addr}) = {before}")

        m.write_holding(addr, new_value)          # Function Code 06
        print(f"write_holding({addr}, {new_value})  완료")

        after = m.read_holding(addr, 1)[0]
        ok = after == new_value
        print(f"쓰기 후  read_holding({addr}) = {after}  {'OK' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
