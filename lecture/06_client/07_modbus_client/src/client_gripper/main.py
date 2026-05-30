"""
07. MODBUS CLIENT (로봇 = 마스터) — 그리퍼 열기/닫기 사이클 (client_gripper)

로봇(Master Client) 역할로 전동 그리퍼(Slave Server)를 제어한다.
매뉴얼 5.4.5.1 예제①(XEG 그리퍼 RTU 제어)의 흐름을 PC 시뮬레이터로 재현한다.

흐름:
    ① 모델 확인   : HR[1536] 읽기 → 2624(XEG-64)
    ② 열기        : HR[1600]=1(열기), HR[1601]=5000(50.00mm), HR[1606]=1(실행)
    ③ 완료 대기   : IR[769]==2(Pos) 그리고 HR[1606]==0(실행 플래그 자동 리셋)
    ④ 닫기        : HR[1600]=0(닫기), HR[1606]=1(실행)
    ⑤ 완료 대기   : IR[769]==2 그리고 HR[1606]==0

⚠️ 완료 판정 함정: IR[769]==2 만 보면 직전 동작의 상태가 latch 되어 즉시 통과한다.
   반드시 IR[769]==2 와 HR[1606]==0(실행 플래그 자동 리셋)을 함께 확인한다.

선행: 다른 터미널에서 그리퍼 서버를 띄워 둔다.
    python ../../_shared/gripper_sim.py --port 1503 --host 127.0.0.1
실행:
    python src/client_gripper/main.py --port 1503
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


def run_gripper(m, direction, stroke_001mm=5000, speed_001mm=5000):
    """그리퍼 한 동작(열기/닫기)을 보내고 완료까지 폴링한다.

    direction : 1=열기 / 0=닫기
    완료 판정 : IR[769]==2(Pos) **그리고** HR[1606]==0(실행 플래그 자동 리셋).
                IR[769] 만 보면 직전 동작 상태가 latch 되어 잘못 통과한다.
    """
    m.write_holding(1600, direction)      # ① 방향 (0=닫기 / 1=열기)
    m.write_holding(1601, stroke_001mm)   # ② 이동 행정 (0.01mm 단위)
    m.write_holding(1602, speed_001mm)    # ③ 이동 속도 (0.01mm/s 단위)
    m.write_holding(1606, 1)              # ④ 실행 트리거
    # ⑤ IR769==2 와 HR1606==0 을 함께 확인 (latch 함정 회피)
    while not (m.read_input(769, 1)[0] == 2 and m.read_holding(1606, 1)[0] == 0):
        time.sleep(0.05)
    return m.read_input(769, 1)[0], m.read_input(770, 1)[0]


def main():
    ap = argparse.ArgumentParser(description="그리퍼 열기/닫기 사이클 (로봇=마스터)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1503)
    args = ap.parse_args()

    print("=== 그리퍼 제어 사이클 (로봇 = Master Client) ===")
    try:
        with RobotMaster(args.host, args.port) as m:   # MBC_TCP_OPEN(1,"...",502)
            # ① 모델 확인
            model = m.read_holding(1536, 1)[0]
            name = "XEG-64" if model == 2624 else f"unknown({model})"
            print(f"[①] 모델 확인 HR[1536]={model}  ->  {name}")

            # ② 열기 50.00mm
            print("[②] 열기 명령: HR[1600]=1, HR[1601]=5000, HR[1606]=1")
            st, pos = run_gripper(m, 1, 5000)
            print(f"[③] 열기 완료  IR[769]={st}(Pos), IR[770]={pos}(= {pos/100:.2f}mm), "
                  f"HR[1606]={m.read_holding(1606, 1)[0]}(자동 리셋)")

            # ④ 닫기
            print("[④] 닫기 명령: HR[1600]=0, HR[1606]=1")
            st, pos = run_gripper(m, 0, 5000)
            print(f"[⑤] 닫기 완료  IR[769]={st}(Pos), IR[770]={pos}(= {pos/100:.2f}mm)")

        print("그리퍼 제어 사이클 완료 ✅")
        return 0
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        print("  그리퍼 서버가 떠 있는지 확인: "
              "python ../../_shared/gripper_sim.py --port "
              f"{args.port} --host {args.host}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
