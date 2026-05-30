"""
정답 1 — 그리퍼 상태(IR769) 사람이 읽는 문자열로 모니터링

핵심 포인트:
- 로봇(Master Client)이 그리퍼의 Input Register IR[769]를 폴링해 상태를 감시한다.
- IR[769] 값(0~3)을 Idle/Busy/Pos/Hold 문자열로 매핑해 사람이 읽게 출력한다.
- 완료 판정은 IR[769]==2 만으로는 부족하다. 직전 동작의 상태가 latch 되어 즉시
  통과하므로, HR[1606]==0(실행 플래그 자동 리셋)을 함께 확인해야 한다.

흔한 실수:
- IR[769]==2 만 보고 완료로 판단 -> 직전 latch 값에 즉시 통과한다.
- 부트스트랩 누락 -> ModuleNotFoundError: modbus_master
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

# IR[769] 상태 코드 -> 사람이 읽는 문자열
STATUS = {0: "Idle", 1: "Busy", 2: "Pos", 3: "Hold"}


def status_str(code):
    return STATUS.get(code, f"Alarm({code})")


def main():
    ap = argparse.ArgumentParser(description="그리퍼 상태 모니터링 (IR769)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1503)
    args = ap.parse_args()

    print("=== 그리퍼 상태 모니터링 (IR[769]) ===")
    try:
        with RobotMaster(args.host, args.port) as m:
            code = m.read_input(769, 1)[0]
            print(f"동작 전 상태 IR[769]={code}  ->  {status_str(code)}")

            # 열기 명령을 보내고 상태 변화를 폴링하며 출력한다.
            m.write_holding(1600, 1)      # 열기
            m.write_holding(1601, 5000)   # 50.00mm
            m.write_holding(1606, 1)      # 실행
            print("열기 명령 전송 -> 상태 폴링 시작")

            seen = []
            # IR769==2 와 HR1606==0 을 함께 확인 (latch 함정 회피).
            # Pos(2)는 완료 신호이므로 루프 안에서는 진행 중 상태(0/1)만 찍고,
            # 최종 Pos 도달은 루프 종료 후 한 번만 출력한다.
            while not (m.read_input(769, 1)[0] == 2 and m.read_holding(1606, 1)[0] == 0):
                code = m.read_input(769, 1)[0]
                if code != 2 and (not seen or seen[-1] != code):
                    seen.append(code)
                    print(f"  IR[769]={code}  ->  {status_str(code)}")
                time.sleep(0.02)

            code = m.read_input(769, 1)[0]
            pos = m.read_input(770, 1)[0]
            if not seen or seen[-1] != code:
                seen.append(code)
            print(f"  IR[769]={code}  ->  {status_str(code)}  (위치 IR[770]={pos} = {pos/100:.2f}mm)")
            print(f"관찰된 상태 흐름: {' -> '.join(status_str(c) for c in seen)}")

        print("상태 모니터링 완료 ✅")
        return 0
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        print("  그리퍼 서버 확인: python ../../_shared/gripper_sim.py --port "
              f"{args.port} --host {args.host}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
