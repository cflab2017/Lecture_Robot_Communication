"""
정답 1 — GO HOME 명령 사이클

핵심 포인트:
- GO HOME(명령번호 4)은 파라미터가 명령번호 1개뿐이라 가장 단순한 사이클이다.
  HR[201]=4 만 쓰면 ①②가 끝나고, 바로 ③ 트리거로 넘어간다.
- 명령 실행 5단계는 모든 명령에 공통이다: 번호 -> (파라미터) -> 트리거 -> 완료대기 -> 리셋.
- GO HOME 후에는 관절/직교 위치가 모두 0(원점)으로 돌아온다.

흔한 실수:
- 마지막 HR[200]<-0 리셋을 빠뜨려 다음 명령이 잠기는 것.
- IR[524](동작상태)가 Idle 이 되기 전에 IR[200]을 읽어 진행중(0)을 성공으로 오해하는 것.

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


def main():
    ap = argparse.ArgumentParser(description="GO HOME 명령 사이클")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1502)
    args = ap.parse_args()

    print("=== GO HOME 명령 사이클 ===")
    try:
        with RobotMaster(args.host, args.port) as m:
            m.write_holding(201, 4)        # ①② GO HOME 은 파라미터가 명령번호뿐
            m.write_holding(200, 1)        # ③ 실행 트리거
            print("HR[201]<-4(GO HOME), HR[200]<-1  트리거")

            # ④ 직전 명령의 Success/Idle 가 남아 있을 수 있으므로,
            #    이번 명령 시작(Running=2)을 먼저 기다린 뒤 완료를 기다린다.
            while m.read_input(524, 1)[0] != 2:
                time.sleep(0.02)
            while not (m.read_input(524, 1)[0] == 1 and m.read_input(200, 1)[0] == 1):
                time.sleep(0.05)
            print(f"완료: IR[524]={m.read_input(524, 1)[0]}(Idle), "
                  f"IR[200]={m.read_input(200, 1)[0]}(Success)")

            joints = m.read_input(300, 12)
            allzero = "모두 0" if all(v == 0 for v in joints) else "주의: 0이 아님"
            print(f"현재 관절 IR[300:312] = {joints}  ({allzero})")

            m.write_holding(200, 0)        # ⑤ 트리거 리셋
            print("HR[200]<-0  리셋")

        print("GO HOME 완료 ✅")
        return 0
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
