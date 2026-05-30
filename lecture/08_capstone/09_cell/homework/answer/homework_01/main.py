"""
정답 1 — {TRIG2} 음수 좌표로 한 사이클 수행

핵심 포인트:
- 비전 트리거를 {TRIG2} 로 주면 음수 좌표 {-45.10, 210.00, -15.0} 가 온다.
- split_word(round(-45.10*1000)) 는 High word 가 음수(-1)인 (Low, High) 를 돌려준다.
  RobotMaster.write_holding 이 각 word 를 & 0xFFFF 로 인코딩해 그대로 보낸다 → 음수도 왕복.
- 한 사이클 후 로봇 직교 현재값 IR400~411 을 되읽어 X 가 정확히 -45.10 으로 들어갔는지 확인.

검증된 함정(셀 컨트롤러와 동일):
- 로봇 완료는 2단계 폴링: 먼저 IR524==2(Running) 시작을 본 뒤 IR524==1(Idle) & IR200==1.
  (직전 명령의 Idle latch 를 피한다. 한 번에 Idle 만 보면 새 명령 시작 전에 통과.)
- HR200=0 리셋 직후 곧바로 다음 트리거를 쓰면 로봇이 리셋을 못 봐서 명령이 잠긴다 → 리셋 후 잠깐 대기.
- 그리퍼 완료는 IR769==2 '그리고' HR1606==0 을 함께 확인(잔상 회피).

실행(3개 시뮬레이터를 각각 다른 포트로 띄운 뒤):
  python ../../_shared/tcp_echo_server.py  --mode vision --port 6000
  python ../../_shared/robot_server_sim.py  --port 1502 --host 127.0.0.1
  python ../../_shared/gripper_sim.py        --port 1503 --host 127.0.0.1
  python homework/answer/homework_01/main.py
  python homework/answer/homework_01/main.py --vision-port 6000 --robot-port 1502 --gripper-port 1503
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
import socket    # noqa: E402
import time      # noqa: E402

from modbus_master import RobotMaster          # noqa: E402
from word_tools import split_word, combine_word  # noqa: E402

APPROACH_Z, PICK_Z = 50.0, 5.0
PLACE_X, PLACE_Y = 200.0, 0.0
GRIP_STROKE, OPEN_STROKE = 4000, 6000
POLL, TIMEOUT = 0.05, 10.0


def get_vision(host, port, trig):
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall(("{" + trig + "}").encode("ascii"))
        raw = s.recv(1024).decode("ascii", errors="replace")
    parts = [p.strip() for p in raw.replace("{", "").replace("}", "").strip().split(",")]
    x, y, r = float(parts[0]), float(parts[1]), float(parts[2])
    print(f"[비전] {trig} → X={x} Y={y} R={r}")
    return x, y, r


def _wait_robot(m):
    """2단계: Running(2) 시작을 본 뒤 Idle(1)&Success(1) 완료."""
    t0 = time.time()
    while m.read_input(524, 1)[0] != 2:
        if time.time() - t0 > TIMEOUT:
            raise TimeoutError("로봇 시작 신호(IR524=2) 시간 초과")
        time.sleep(POLL)
    while not (m.read_input(524, 1)[0] == 1 and m.read_input(200, 1)[0] == 1):
        if time.time() - t0 > TIMEOUT:
            raise TimeoutError("로봇 완료 신호(IR524=1 & IR200=1) 시간 초과")
        time.sleep(POLL)


def robot_move(m, x, y, z, c=0.0, cmd=1, label=""):
    axis = []
    for v in (x, y, z, 0.0, 0.0, c):
        low, high = split_word(round(v * 1000))
        axis += [low, high]
    m.write_holding(201, [cmd, 1] + axis + [50, 100, 1, 0])
    m.write_holding(200, 1)
    _wait_robot(m)
    m.write_holding(200, 0)
    time.sleep(POLL * 2)        # 리셋 인지 대기 (안 하면 다음 명령 잠김)
    print(f"[로봇] {label} 완료")


def gripper_act(m, direction, stroke, label=""):
    m.write_holding(1600, direction)
    m.write_holding(1601, stroke)
    m.write_holding(1606, 1)
    t0 = time.time()
    while not (m.read_input(769, 1)[0] == 2 and m.read_holding(1606, 1)[0] == 0):
        if time.time() - t0 > TIMEOUT:
            raise TimeoutError("그리퍼 완료 신호(IR769=2 & HR1606=0) 시간 초과")
        time.sleep(POLL)
    print(f"[그리퍼] {label} 완료 (IR770={m.read_input(770, 1)[0]})")


def read_cartesian(m):
    w = m.read_input(400, 12)
    out = []
    for i in range(0, 12, 2):
        low = w[i] if w[i] < 32768 else w[i] - 65536
        high = w[i + 1] if w[i + 1] < 32768 else w[i + 1] - 65536
        out.append(round(combine_word(low, high) * 0.001, 3))
    return out


def main():
    ap = argparse.ArgumentParser(description="과제1 — TRIG2 음수 좌표 한 사이클")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--vision-port", type=int, default=6000)
    ap.add_argument("--robot-port", type=int, default=1502)
    ap.add_argument("--gripper-port", type=int, default=1503)
    args = ap.parse_args()

    print("=== 과제1: {TRIG2} 음수 좌표 픽앤플레이스 ===")
    x, y, r = get_vision(args.host, args.vision_port, "TRIG2")
    with RobotMaster(args.host, args.robot_port) as robot, \
         RobotMaster(args.host, args.gripper_port) as gripper:
        robot_move(robot, x, y, APPROACH_Z, c=r, label=f"픽 접근 (X={x})")
        robot_move(robot, x, y, PICK_Z, c=r, label="픽 하강")
        cart = read_cartesian(robot)        # 픽 하강 직후 직교 현재값 확인
        gripper_act(gripper, 0, GRIP_STROKE, label="집기")
        robot_move(robot, x, y, APPROACH_Z, c=r, label="픽 상승")
        robot_move(robot, PLACE_X, PLACE_Y, APPROACH_Z, label="플레이스 이동")
        gripper_act(gripper, 1, OPEN_STROKE, label="놓기")
        robot_move(robot, 0.0, 0.0, 0.0, cmd=4, label="GO HOME")  # 명령4=GO HOME

    print("-" * 40)
    print(f"픽 위치 IR400~411 디코딩 X..C = {cart}")
    ok = abs(cart[0] - x) < 1e-6
    print(f"음수 좌표 왕복: X={cart[0]} (기대 {x})  {'OK' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
