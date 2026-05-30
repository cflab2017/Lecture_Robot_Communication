"""
06. MODBUS SERVER (로봇 = 슬레이브) — PTP 명령 사이클 (server_motion)

마스터(상위 PLC) 역할로 로봇 슬레이브에 PTP 명령을 한 사이클 보낸다.
목표: A1 관절을 90.000° 로 PTP(Joint) 이동.

매뉴얼 5.3.3.5 명령 실행 절차를 그대로 수행한다:
    ① HR[201] <- 명령번호(0=PTP)
    ② HR[202~218] <- 파라미터(모션타입/6축 L-H/속도/가속/Tool/Base)
    ③ HR[200] <- 1            (실행 트리거)
    ④ IR[524] 2(Run)->1(Idle) & IR[200]=1(Success) 될 때까지 폴링
    ⑤ HR[200] <- 0           (마스터가 리셋 -> 다음 명령 준비)

90° 가 (24464, 1) 인 이유: 90.000° = 90×1000 = 90000.
16bit 한 word(-32768~32767)에 안 들어가므로 split_word() 로 분할한다.
    Low  = 90000 % 65536 = 24464
    High = 90000 // 65536 = 1
    복원 = 1×65536 + 24464 = 90000 -> ×0.001 = 90.000°

선행: 다른 터미널에서 로봇 슬레이브를 띄워 둔다.
    python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1
실행:
    python src/server_motion/main.py --port 1502
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

import argparse  # noqa: E402
import time  # noqa: E402

from modbus_master import RobotMaster  # noqa: E402
from word_tools import split_word  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="PTP 명령 사이클 (로봇=슬레이브)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1502)
    args = ap.parse_args()

    A1_low, A1_high = split_word(90000)        # (24464, 1) = 90.000°

    print("=== PTP 명령 사이클 (A1=90° 각도 이동) ===")
    try:
        with RobotMaster(args.host, args.port) as m:
            # ① HR201=명령번호, ② HR202~218=파라미터 를 한 번에 쓴다.
            #   HR201 명령번호 0 = PTP
            #   HR202 모션타입 0 = Joint
            #   HR203~214 6축 L/H (A1=24464,1 / A2~A6=0)
            #   HR215~218 속도50% / 가속100% / Tool1 / Base2
            params = [0,                                  # 201 명령번호 PTP
                      0,                                  # 202 모션타입 Joint
                      A1_low, A1_high,                    # 203/204 A1
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,       # 205~214 A2~A6
                      50, 100, 1, 2]                      # 215~218
            m.write_holding(201, params)
            print(f"[①] HR[201]=0(PTP), HR[202]=0(Joint), "
                  f"HR[203:205]={[A1_low, A1_high]}  (split_word(90000))")
            print(f"[②] HR[215:219]=[50, 100, 1, 2]  속도50% / 가속100% / Tool1 / Base2")

            m.write_holding(200, 1)                       # ③ 실행 트리거
            print("[③] HR[200]<-1  실행 트리거")

            # ④ 동작 완료 대기.
            #   직전 명령의 Success(IR200=1)·Idle(IR524=1)가 남아 있을 수 있으므로
            #   먼저 이번 명령이 시작(Running=2)되기를 기다린 뒤 완료를 기다린다.
            while m.read_input(524, 1)[0] != 2:
                time.sleep(0.02)
            while not (m.read_input(524, 1)[0] == 1 and m.read_input(200, 1)[0] == 1):
                time.sleep(0.05)
            joint = m.read_input(300, 2)                  # 현재 관절 A1 L/H
            angle = (joint[1] * 65536 + joint[0]) * 0.001
            print(f"[④] 동작 완료 대기... IR[524]={m.read_input(524, 1)[0]}(Idle), "
                  f"IR[200]={m.read_input(200, 1)[0]}(Success)")
            print(f"    현재 관절 IR[300:302] = {joint}  ->  {angle:.3f}°")

            m.write_holding(200, 0)                       # ⑤ 트리거 리셋
            print("[⑤] HR[200]<-0  트리거 리셋 (다음 명령 준비)")

        print("PTP 사이클 완료 ✅")
        return 0
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        print("  로봇 슬레이브가 떠 있는지 확인: "
              "python ../../_shared/robot_server_sim.py --port "
              f"{args.port} --host {args.host}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
