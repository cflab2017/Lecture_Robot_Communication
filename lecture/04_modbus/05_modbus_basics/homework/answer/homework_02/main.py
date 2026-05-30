"""
정답 2 — 읽기 전용 레지스터에는 쓸 수 없음을 확인하기

핵심 포인트:
- Input Register 와 Discrete Input 은 '읽기 전용(R)' 이다. MODBUS 표준에도
  이 둘을 쓰는 Function Code 자체가 없다(01/02/03/04 = 읽기뿐).
- 그래서 마스터 래퍼 RobotMaster 에도 write_input / write_discrete 메서드가
  '아예 존재하지 않는다'. 호출을 시도하면 AttributeError 가 난다.
- 권한이 코드 레벨에서 강제됨을 try/except 로 잡아 친절히 설명한다.
- 반대로 Holding Register 는 R/W 라 정상적으로 써지는 것을 대비로 보여준다.

흔한 실수:
- write-ir / write-di 같은 명령이 거부되는 것을 '버그' 로 오해하는 것.
  이는 버그가 아니라 읽기/쓰기 권한 설계가 강제된 정상 동작이다.
- 읽기 전용 값(동작상태·외부 입력 신호)을 마스터가 덮어쓰려 하는 것.
  이 값들은 슬레이브(로봇)가 채우는 값이므로 읽기만 한다.

실행:
    # 터미널 1: python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1
    # 터미널 2:
    python homework_02/main.py --port 1502
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


def try_write_readonly(m, kind, addr, value):
    """읽기 전용 레지스터에 쓰기를 시도한다. write 메서드가 없어 실패해야 정상."""
    method = getattr(m, f"write_{kind}", None)   # write_input / write_discrete
    if method is None:
        print(f"  [차단] {kind} 은 읽기 전용 → write_{kind}() 메서드가 없습니다. (설계상 정상)")
        return False
    try:
        method(addr, value)
        print(f"  [경고] {kind} 쓰기가 통과했습니다 — 읽기 전용이어야 하는데 이상합니다.")
        return True
    except Exception as e:
        print(f"  [차단] {kind} 쓰기 실패: {type(e).__name__}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1502)
    ap.add_argument("--unit", type=int, default=1)
    args = ap.parse_args()

    with RobotMaster(args.host, args.port, args.unit) as m:
        print("[1] 읽기 전용 레지스터에 쓰기 시도 — 실패해야 정상입니다.")
        # Input Register 524 = 동작상태(슬레이브가 채우는 값)
        try_write_readonly(m, "input", 524, 2)
        # Discrete Input 3 = SO4(Ready, 로봇 상태 출력)
        try_write_readonly(m, "discrete", 3, 0)

        print("     읽기 전용 값은 그대로 유지됩니다:")
        print(f"       read_input(524,1)  = {m.read_input(524, 1)}")
        print(f"       read_discrete(0,8) = {[int(b) for b in m.read_discrete(0, 8)]}")

        print("\n[2] 대비 — R/W 레지스터(Holding)는 정상적으로 써집니다.")
        m.write_holding(100, 60)                  # Function Code 06
        after = m.read_holding(100, 1)[0]
        print(f"     write_holding(100, 60) 후 read_holding(100,1) = [{after}]  "
              f"{'OK' if after == 60 else 'FAIL'}")

        print("\n결론: 권한 표(DI·IR=R, Coil·HR=R/W)가 실제로 강제됩니다.")


if __name__ == "__main__":
    main()
