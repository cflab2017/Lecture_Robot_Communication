"""
09. 종합 실습 — 비전·로봇·그리퍼 자동화 셀 (cell_controller)

상위 비전 시스템이 부품 위치를 알려주면(TCP/IP), 로봇이 그 좌표로 이동(Modbus)해
그리퍼로 집고(Modbus), 지정 위치에 놓고 원점으로 복귀한다. 즉 03편(TCP/IP) +
06편(로봇=Server, 명령 사이클) + 07편(그리퍼=Client 제어) + 08편(모니터링)을
한 스크립트로 묶은 통합 컨트롤러다.

이 컨트롤러는 "셀 제어기(상위 컨트롤러/PLC)" 역할이다.
  - 비전(상위 시스템)에게는 TCP Client 로 접속해 {TRIG} 를 보내고 좌표를 받는다.
  - 로봇(Modbus Server/Slave)에게는 Modbus Master 로 명령 사이클을 돌린다.
  - 그리퍼(Modbus Server/Slave)에게도 Modbus Master 로 열기/닫기 명령을 보낸다.

3개 시뮬레이터를 각각 다른 포트로 띄워두고 실행한다.
  터미널 1 : python ../../_shared/tcp_echo_server.py  --mode vision --port 6000
  터미널 2 : python ../../_shared/robot_server_sim.py  --port 1502 --host 127.0.0.1
  터미널 3 : python ../../_shared/gripper_sim.py        --port 1503 --host 127.0.0.1
  터미널 4 : python src/cell_controller/main.py              # 한 사이클 실행
            python src/cell_controller/main.py --trig TRIG2  # 음수 좌표(과제 1)
            python src/cell_controller/main.py --cycles 2    # TRIG→TRIG2 반복(과제 2)

종료: 컨트롤러는 한 사이클(또는 지정 횟수) 후 자동 종료. 시뮬레이터는 Ctrl+C.
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
import socket    # noqa: E402
import time      # noqa: E402

from modbus_master import RobotMaster   # noqa: E402  로봇/그리퍼를 제어하는 Modbus 마스터
from word_tools import split_word       # noqa: E402  좌표 32bit → Low/High word 분할


# ── 셀 동작 파라미터 (필요 시 현장 값으로 조정) ────────────────────────────
APPROACH_Z = 50.0     # 접근 높이 [mm] : 부품 위 안전 높이
PICK_Z = 5.0          # 픽 높이   [mm] : 실제로 집는 높이
PLACE_X = 200.0       # 플레이스 위치 X [mm]
PLACE_Y = 0.0         # 플레이스 위치 Y [mm]
PLACE_Z = APPROACH_Z  # 플레이스는 접근 높이에서 놓는다(단순화)
GRIP_STROKE = 4000    # 그립 행정 [0.01mm] = 40.00mm (부품을 잡는 폭)
OPEN_STROKE = 6000    # 열기 행정 [0.01mm] = 60.00mm
SPEED = 50            # 속도 %
ACCEL = 100           # 가속 %
TOOL = 1              # Tool 번호
BASE = 0              # Base 번호
POLL = 0.05           # 상태 폴링 주기 [s]
TIMEOUT = 10.0        # 단계별 완료 대기 한계 [s]


def log(step, msg):
    print(f"  [{step}] {msg}")


# ── 1) 비전 : TCP/IP 로 좌표 받기 (03편) ──────────────────────────────────
def get_vision(host, port, trig="TRIG"):
    """비전 시스템에 {TRIG} 를 보내고 {X,Y,R} 을 받아 (x, y, r) float 로 파싱."""
    print(f"[1] 비전 시스템({host}:{port})에 부품 위치 요청 …")
    try:
        with socket.create_connection((host, port), timeout=5) as s:
            req = "{" + trig + "}"
            s.sendall(req.encode("ascii"))
            log("VISION", f"송신 {req}")
            raw = s.recv(1024).decode("ascii", errors="replace")
    except OSError as e:
        raise ConnectionError(
            f"비전 서버 연결 실패({host}:{port}). "
            f"'python ../../_shared/tcp_echo_server.py --mode vision --port {port}' 가 떠 있나요? ({e})"
        )
    log("VISION", f"수신 {raw.strip()}")
    payload = raw.replace("{", "").replace("}", "").strip()
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) < 3:
        raise ValueError(f"비전 응답 형식 오류: {raw!r} (X,Y,R 3개 필요)")
    x, y, r = float(parts[0]), float(parts[1]), float(parts[2])
    print(f"    → 부품 좌표  X={x} mm  Y={y} mm  회전각 R={r} deg")
    return x, y, r


# ── 2) 로봇 : Modbus 명령 사이클로 직교 이동 (06편) ──────────────────────────
def robot_move(m, x, y, z, a=0.0, b=0.0, c=0.0, cmd=1, mtype=1, label=""):
    """직교(Cartesian) LIN 이동 한 사이클.

    좌표 6축(X,Y,Z,A,B,C)을 각각 ×1000 정수화 후 split_word() 로 Low/High 분할해
    HR203~214 에 채운다. write_holding() 이 음수 word 를 자동으로 0xFFFF 인코딩하므로
    음수 좌표(예: TRIG2 의 X=-45.10)도 그대로 전달하면 된다.

    명령 사이클(매뉴얼 5.3.3.5):
      ① HR201=명령번호, HR202=모션타입, HR203~214=6축, HR215~218=속도/가속/Tool/Base
      ② HR200=1 (실행 트리거)
      ③ IR524 가 2(Running)로 올라온 뒤 1(Idle) & IR200==1(Success) 가 될 때까지 폴링
      ④ HR200=0 (리셋 — 안 하면 다음 명령이 잠긴다)
    """
    axis = []
    for v in (x, y, z, a, b, c):
        low, high = split_word(round(v * 1000))   # ×1000 정수화 후 32bit 분할
        axis += [low, high]                        # [L, H] 순서로 12워드
    params = [cmd, mtype] + axis + [SPEED, ACCEL, TOOL, BASE]   # HR201~218
    label = label or f"({x}, {y}, {z})"
    print(f"[로봇] LIN 이동 → {label}")
    m.write_holding(201, params)        # ① HR201~218 한 번에 쓰기
    m.write_holding(200, 1)             # ② 실행 트리거
    _wait_robot(m)                      # ③ 완료 폴링 (2단계)
    _reset_robot_trigger(m)             # ④ 트리거 리셋 + 로봇이 리셋을 인지하도록 대기
    log("ROBOT", "이동 완료 (IR200=1 Success, IR524=1 Idle)")


def _wait_robot(m):
    """로봇 완료를 2단계로 기다린다.

    ⚠️ 함정 ①: IR524 만 한 번에 'Idle(1)' 로 보면, 직전 명령이 이미 Idle 로
       남아 있어(상태 잔상/latch) 새 명령이 시작하기도 전에 통과해 버린다.
       그래서 (1) 먼저 IR524==2(Running) 로 올라오는 것을 확인해 '이번 명령이
       시작됐음' 을 잡고, (2) 그 뒤 IR524==1(Idle) & IR200==1(Success) 로 완료를
       판정한다. (그리퍼의 HR1606==0 동반 확인과 같은 종류의 잔상 회피)
    """
    t0 = time.time()
    # (1) Running(2) 시작을 기다린다 — 직전 Idle latch 회피
    while m.read_input(524, 1)[0] != 2:
        if time.time() - t0 > TIMEOUT:
            raise TimeoutError("로봇 동작 시작 신호(IR524=2 Running) 시간 초과")
        time.sleep(POLL)
    # (2) Idle(1) & Success(1) 완료를 기다린다
    while not (m.read_input(524, 1)[0] == 1 and m.read_input(200, 1)[0] == 1):
        if time.time() - t0 > TIMEOUT:
            raise TimeoutError("로봇 동작 완료 신호(IR524=1 & IR200=1) 시간 초과")
        time.sleep(POLL)


def _reset_robot_trigger(m):
    """HR200=0 으로 트리거를 리셋하고, 로봇이 그 리셋을 '인지' 하도록 잠깐 둔다.

    ⚠️ 함정 ②: 로봇은 완료 후 마스터가 HR200 을 0 으로 되돌리기를 기다리는
       'ack 대기' 상태에 들어간다(매뉴얼 5.3.3.5 절차 ⑤). HR200=0 직후 곧바로
       다음 명령의 HR200=1 을 쓰면, 로봇 로직이 '0' 을 한 번도 보지 못해 ack 가
       풀리지 않고 다음 명령이 통째로 무시(잠김)된다. 폴링 한두 주기만큼만
       비워 둬서 로봇이 리셋을 확실히 관측하게 한다.
    """
    m.write_holding(200, 0)
    time.sleep(POLL * 2)


def go_home(m):
    """원점 복귀(GO HOME = 명령번호 4)로 사이클 마무리."""
    print("[로봇] GO HOME (원점 복귀) …")
    m.write_holding(201, 4)             # ① 명령번호 4 = GO HOME
    m.write_holding(200, 1)             # ② 실행 트리거
    _wait_robot(m)                      # ③ 완료 폴링 (2단계)
    _reset_robot_trigger(m)             # ④ 트리거 리셋 + 인지 대기
    log("ROBOT", "원점 복귀 완료 (IR400~411 = 0)")


# ── 3) 그리퍼 : Modbus 로 집기/놓기 (07편) ────────────────────────────────
def gripper_act(m, direction, stroke):
    """그리퍼 한 동작. direction 0=닫기(집기) / 1=열기(놓기).

    절차(매뉴얼 5.4.5.1):
      ① HR1600=방향, ② HR1601=행정, ③ HR1606=1 (실행)
      ④ 완료 폴링 — IR769==2(Pos 도달) **그리고** HR1606==0(자동 복귀) 동시 확인.

    ⚠️ IR769 만 보면 직전 동작의 잔상(Pos=2)이 남아 새 동작이 끝나기 전에 루프를
      빠져나가는 경합(race)이 생긴다. 그리퍼가 완료 시 스스로 0으로 되돌리는
      HR1606 을 함께 확인해 "이번 동작의 완료" 를 분명히 한다.
    """
    name = "열기(놓기)" if direction == 1 else "닫기(집기)"
    print(f"[그리퍼] {name} → 행정 {stroke / 100:.2f} mm")
    m.write_holding(1600, direction)    # ① 방향
    m.write_holding(1601, stroke)       # ② 이동 행정
    m.write_holding(1606, 1)            # ③ 실행 트리거
    t0 = time.time()
    while not (m.read_input(769, 1)[0] == 2 and m.read_holding(1606, 1)[0] == 0):  # ④
        if time.time() - t0 > TIMEOUT:
            raise TimeoutError("그리퍼 완료 신호(IR769=2 & HR1606=0) 시간 초과")
        time.sleep(POLL)
    pos = m.read_input(770, 1)[0]
    flag = m.read_holding(1606, 1)[0]
    log("GRIPPER", f"완료 (IR769=2 Pos, IR770={pos}={pos / 100:.2f}mm, HR1606={flag} 자동복귀)")


# ── 전체 픽앤플레이스 사이클 ───────────────────────────────────────────────
def run_cycle(args, trig, robot, gripper):
    """비전→로봇→그리퍼 한 사이클. robot/gripper 는 열린 RobotMaster."""
    t0 = time.time()
    x, y, r = get_vision(args.host, args.vision_port, trig)

    print("[2] 픽 동작 (접근 → 하강 → 집기) …")
    robot_move(robot, x, y, APPROACH_Z, c=r, label=f"픽 접근 ({x},{y},Z={APPROACH_Z})")
    robot_move(robot, x, y, PICK_Z, c=r, label=f"픽 하강 ({x},{y},Z={PICK_Z})")
    gripper_act(gripper, 0, GRIP_STROKE)                      # 닫기 = 집기
    robot_move(robot, x, y, APPROACH_Z, c=r, label=f"픽 상승 ({x},{y},Z={APPROACH_Z})")

    print("[3] 플레이스 동작 (이동 → 놓기) …")
    robot_move(robot, PLACE_X, PLACE_Y, PLACE_Z, label=f"플레이스 이동 ({PLACE_X},{PLACE_Y},Z={PLACE_Z})")
    gripper_act(gripper, 1, OPEN_STROKE)                      # 열기 = 놓기

    print("[4] 마무리 …")
    go_home(robot)
    dt = time.time() - t0
    print(f"=== 사이클 완료 (cycle time {dt:.2f}s) ===\n")
    return dt


def main():
    ap = argparse.ArgumentParser(description="비전·로봇·그리퍼 자동화 셀 컨트롤러")
    ap.add_argument("--host", default="127.0.0.1",
                    help="세 장치 공통 호스트 (기본 127.0.0.1)")
    ap.add_argument("--vision-port", type=int, default=6000, help="비전(TCP) 포트")
    ap.add_argument("--robot-port", type=int, default=1502, help="로봇(Modbus) 포트")
    ap.add_argument("--gripper-port", type=int, default=1503, help="그리퍼(Modbus) 포트")
    ap.add_argument("--trig", default="TRIG", help="비전 트리거 토큰 (TRIG / TRIG2)")
    ap.add_argument("--cycles", type=int, default=1,
                    help="반복 횟수. 2 이상이면 TRIG→TRIG2→TRIG… 번갈아 처리(과제 2)")
    args = ap.parse_args()

    print("=" * 60)
    print(" 비전·로봇·그리퍼 자동화 셀 컨트롤러 시작")
    print(f"  비전  {args.host}:{args.vision_port}  (TCP)")
    print(f"  로봇  {args.host}:{args.robot_port}  (Modbus)")
    print(f"  그리퍼 {args.host}:{args.gripper_port}  (Modbus)")
    print("=" * 60)

    trig_seq = ["TRIG", "TRIG2"]
    times = []
    try:
        # 로봇·그리퍼 연결은 한 번 열어 여러 사이클에 재사용
        with RobotMaster(args.host, args.robot_port) as robot, \
             RobotMaster(args.host, args.gripper_port) as gripper:
            for i in range(args.cycles):
                trig = args.trig if args.cycles == 1 else trig_seq[i % len(trig_seq)]
                print(f"\n----- 사이클 {i + 1}/{args.cycles}  (trigger {trig}) -----")
                times.append(run_cycle(args, trig, robot, gripper))
    except ConnectionError as e:
        print(f"\n[연결 오류] {e}", file=sys.stderr)
        sys.exit(1)
    except (TimeoutError, ValueError, IOError) as e:
        print(f"\n[동작 오류] {e}", file=sys.stderr)
        sys.exit(2)

    if times:
        print("=" * 60)
        print(f" 전체 {len(times)} 사이클 완료. "
              f"평균 cycle time {sum(times) / len(times):.2f}s "
              f"(min {min(times):.2f}s / max {max(times):.2f}s)")
        print("=" * 60)


if __name__ == "__main__":
    main()
