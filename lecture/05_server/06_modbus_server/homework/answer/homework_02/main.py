"""
정답 2 — 직교 LIN 으로 X=-300mm 이동 후 좌표 복원

핵심 포인트:
- LIN(명령번호 1) + 모션타입 Cartesian(1) 로 직교 X 를 이동시킨다.
- split_word(-300000) = (27680, -5) 로 High word 가 음수(-5)다.
  Modbus 레지스터 쓰기는 unsigned 16bit 만 받지만, RobotMaster.write_holding() 이
  내부에서 (v & 0xFFFF) 로 자동 인코딩한다(-5 -> 65531). 그래서 음수 word 를
  그대로 넣어도 struct.error 가 나지 않는다.
- 응답(IR[400:402])은 unsigned 로 읽히므로([27680, 65531]) signed 로 복원해야
  원래 좌표 -300.000mm 가 나온다. (signed↔unsigned 는 같은 16bit 의 두 해석)

흔한 실수:
- 응답을 unsigned 그대로 combine 해 65531×65536+... 같은 거대한 양수를 얻는 것.
  -> 32767 초과 word 는 (raw - 65536) 으로 먼저 signed 화한다.
- 마지막 HR[200]<-0 리셋 누락으로 다음 명령이 잠기는 것.

선행:  python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1
실행:  python main.py --port 1502
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
import time  # noqa: E402

from modbus_master import RobotMaster  # noqa: E402
from word_tools import combine_word, split_word  # noqa: E402


def to_signed(word):
    """0~65535 unsigned word -> signed 16bit."""
    return word - 65536 if word > 32767 else word


def main():
    ap = argparse.ArgumentParser(description="직교 LIN X=-300mm 명령 사이클")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1502)
    args = ap.parse_args()

    X_low, X_high = split_word(-300000)        # (27680, -5)

    print("=== 직교 LIN 명령 사이클 (X=-300mm) ===")
    try:
        with RobotMaster(args.host, args.port) as m:
            # ①② 명령번호 1=LIN, 모션타입 1=Cartesian, X=(27680,-5), Y~C=0
            params = [1, 1, X_low, X_high,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      50, 100, 1, 2]
            m.write_holding(201, params)       # 음수 High word 는 자동 인코딩
            print(f"HR[201]<-1(LIN), HR[202]<-1(Cartesian), "
                  f"HR[203:205]={[X_low, X_high]}  (split_word(-300000))")

            m.write_holding(200, 1)            # ③ 실행 트리거
            print("HR[200]<-1  트리거")

            # ④ 직전 명령의 Success/Idle 가 남아 있을 수 있으므로,
            #    이번 명령 시작(Running=2)을 먼저 기다린 뒤 완료를 기다린다.
            while m.read_input(524, 1)[0] != 2:
                time.sleep(0.02)
            while not (m.read_input(524, 1)[0] == 1 and m.read_input(200, 1)[0] == 1):
                time.sleep(0.05)
            print(f"완료: IR[524]={m.read_input(524, 1)[0]}(Idle), "
                  f"IR[200]={m.read_input(200, 1)[0]}(Success)")

            raw = m.read_input(400, 2)         # 직교 X 의 L/H (unsigned 로 읽힘)
            lo, hi = to_signed(raw[0]), to_signed(raw[1])
            raw_int = combine_word(lo, hi)
            print(f"직교 X IR[400:402] (raw, unsigned) = {raw}")
            print(f"signed 복원 = ({lo}, {hi})  ->  {raw_int}  ->  "
                  f"{raw_int * 0.001:.3f} mm")

            m.write_holding(200, 0)            # ⑤ 트리거 리셋
            print("HR[200]<-0  리셋")

        print("LIN 사이클 완료 ✅")
        return 0
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
