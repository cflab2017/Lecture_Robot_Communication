"""
05. MODBUS 기초 — 4종 레지스터 직접 읽고/쓰기 (modbus_basics)

robot_server_sim.py 를 "일반 Modbus 슬레이브" 로 보고, 4종 레지스터를
각각 읽은 뒤(Function Code 02/01/04/03) R/W 권한이 있는 Holding/Coil 에
값을 써넣고 다시 읽어 반영을 확인한다.

  - Discrete Input  (R)   : Function Code 02 — SO(로봇 상태 출력)
  - Coil            (R/W) : Function Code 01 읽기 / 05 쓰기 — SI·DO
  - Input Register  (R)   : Function Code 04 — 속도%, 동작상태
  - Holding Register(R/W) : Function Code 03 읽기 / 06 쓰기 — 속도 설정

먼저 다른 터미널에서 슬레이브를 띄워야 한다:
    python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1

실행:  python src/modbus_basics/main.py --port 1502
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

from modbus_master import RobotMaster  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="MODBUS 4종 레지스터 읽기/쓰기 데모")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1502)
    ap.add_argument("--unit", type=int, default=1, help="Slave ID")
    args = ap.parse_args()

    print("=== MODBUS 기초 — 4종 레지스터 직접 다루기 ===")
    print(f"슬레이브 {args.host}:{args.port} (Slave ID {args.unit}) 에 접속합니다.\n")

    with RobotMaster(args.host, args.port, args.unit) as m:
        # --- 1) 읽기: 4종 레지스터를 각각 읽는다 ----------------------------
        print("[읽기] 4종 레지스터를 각각 읽습니다.")

        di = [int(b) for b in m.read_discrete(0, 8)]
        print(f"  ① Discrete Input (FC02) read_discrete(0,8) = {di}")
        print("     -> 주소 3(SO4=Ready)만 1. 로봇이 '준비됨' 상태입니다.")

        co = [int(b) for b in m.read_coils(0, 8)]
        print(f"  ② Coil           (FC01) read_coils(0,8)    = {co}")
        print("     -> SI1~SI8(입력). 아직 켜지 않아 전부 0.")

        ir_speed = m.read_input(100, 1)[0]
        ir_state = m.read_input(524, 1)[0]
        print(f"  ③ Input Register (FC04) read_input(100,1)  = [{ir_speed}]  (속도%)")
        print(f"                          read_input(524,1)  = [{ir_state}]  (동작상태 1=Idle)")

        hr = m.read_holding(100, 1)[0]
        print(f"  ④ Holding Reg    (FC03) read_holding(100,1)= [{hr}]  (속도 설정값)\n")

        # --- 2) 쓰기: R/W 권한 레지스터에 값을 쓰고 다시 읽어 확인 ----------
        print("[쓰기] R/W 권한을 가진 Holding Register / Coil 에 값을 씁니다.")

        # 속도 설정값(Holding Register) 쓰기 — Function Code 06
        m.write_holding(100, 50)
        print("  ⑤ Holding 쓰기 (FC06) write_holding(100, 50)")
        hr_after = m.read_holding(100, 1)[0]
        mark = "✅" if hr_after == 50 else "❌"
        print(f"     재확인 read_holding(100,1) = [{hr_after}]  {mark}")

        # 디지털 출력 DO1(Coil 300) 켜기 — Function Code 05
        m.write_coil(300, 1)
        print("  ⑥ Coil 쓰기    (FC05) write_coil(300, 1)  (DO1 ON)")
        co_after = [int(b) for b in m.read_coils(300, 1)]
        mark = "✅" if co_after == [1] else "❌"
        print(f"     재확인 read_coils(300,1) = {co_after}  {mark}\n")

    print("------------------------------")
    print("4종 레지스터 읽기/쓰기 데모 완료 ✅")


if __name__ == "__main__":
    main()
