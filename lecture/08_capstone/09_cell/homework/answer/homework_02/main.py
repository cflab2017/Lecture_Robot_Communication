"""
정답 2 — 여러 부품 연속 처리 루프(--cycles)와 평균 사이클 타임 출력

핵심 포인트:
- 비전 트리거 TRIG / TRIG2 를 번갈아 주며 부품을 N개 연속 픽앤플레이스 한다.
- 로봇·그리퍼 연결은 '한 번만' 열어(with) 모든 사이클에 재사용한다(매 사이클 새 연결 X).
- 각 사이클의 cycle time 을 측정해 마지막에 평균/최소/최대를 출력한다.

검증된 함정(반복 처리에서 특히 중요):
- 로봇 완료는 2단계 폴링: 먼저 IR524==2(Running) 시작을 본 뒤 IR524==1(Idle) & IR200==1.
  반복 시 직전 사이클의 Idle 가 latch 로 남아 있어, 한 번에 Idle 만 보면 새 명령이
  시작하기도 전에 통과해 좌표가 갱신되지 않은 채 다음으로 넘어간다.
- HR200=0 리셋 직후 곧바로 다음 트리거를 쓰면 로봇이 리셋을 못 봐 명령이 잠긴다 → 리셋 후 잠깐 대기.
- 그리퍼 완료는 IR769==2 '그리고' HR1606==0 함께 확인. IR769 만 보면 직전 동작의
  Pos(2) 잔상으로 다음 동작이 즉시 '완료' 로 오판된다.

실행(3개 시뮬레이터를 각각 다른 포트로 띄운 뒤):
  python ../../_shared/tcp_echo_server.py  --mode vision --port 6000
  python ../../_shared/robot_server_sim.py  --port 1502 --host 127.0.0.1
  python ../../_shared/gripper_sim.py        --port 1503 --host 127.0.0.1
  python homework/answer/homework_02/main.py --cycles 3
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

from modbus_master import RobotMaster   # noqa: E402
from word_tools import split_word       # noqa: E402

APPROACH_Z, PICK_Z = 50.0, 5.0
PLACE_X, PLACE_Y = 200.0, 0.0
GRIP_STROKE, OPEN_STROKE = 4000, 6000
POLL, TIMEOUT = 0.05, 10.0


def get_vision(host, port, trig):
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall(("{" + trig + "}").encode("ascii"))
        raw = s.recv(1024).decode("ascii", errors="replace")
    parts = [p.strip() for p in raw.replace("{", "").replace("}", "").strip().split(",")]
    return float(parts[0]), float(parts[1]), float(parts[2])


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


def robot_move(m, x, y, z, c=0.0, cmd=1):
    axis = []
    for v in (x, y, z, 0.0, 0.0, c):
        low, high = split_word(round(v * 1000))
        axis += [low, high]
    m.write_holding(201, [cmd, 1] + axis + [50, 100, 1, 0])
    m.write_holding(200, 1)
    _wait_robot(m)
    m.write_holding(200, 0)
    time.sleep(POLL * 2)        # 리셋 인지 대기


def gripper_act(m, direction, stroke):
    m.write_holding(1600, direction)
    m.write_holding(1601, stroke)
    m.write_holding(1606, 1)
    t0 = time.time()
    while not (m.read_input(769, 1)[0] == 2 and m.read_holding(1606, 1)[0] == 0):
        if time.time() - t0 > TIMEOUT:
            raise TimeoutError("그리퍼 완료 신호(IR769=2 & HR1606=0) 시간 초과")
        time.sleep(POLL)


def run_cycle(host, vport, trig, robot, gripper):
    t0 = time.time()
    x, y, r = get_vision(host, vport, trig)
    robot_move(robot, x, y, APPROACH_Z, c=r)        # 픽 접근
    robot_move(robot, x, y, PICK_Z, c=r)            # 픽 하강
    gripper_act(gripper, 0, GRIP_STROKE)            # 집기
    robot_move(robot, x, y, APPROACH_Z, c=r)        # 픽 상승
    robot_move(robot, PLACE_X, PLACE_Y, APPROACH_Z)  # 플레이스 이동
    gripper_act(gripper, 1, OPEN_STROKE)            # 놓기
    robot_move(robot, 0.0, 0.0, 0.0, cmd=4)         # GO HOME
    return time.time() - t0


def main():
    ap = argparse.ArgumentParser(description="과제2 — 여러 부품 연속 처리 + 평균 cycle time")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--vision-port", type=int, default=6000)
    ap.add_argument("--robot-port", type=int, default=1502)
    ap.add_argument("--gripper-port", type=int, default=1503)
    ap.add_argument("--cycles", type=int, default=3, help="처리할 부품 개수")
    args = ap.parse_args()

    trig_seq = ["TRIG", "TRIG2"]
    print(f"=== 과제2: {args.cycles}개 부품 연속 처리 ===")
    times = []
    # 연결은 한 번만 열어 모든 사이클에 재사용
    with RobotMaster(args.host, args.robot_port) as robot, \
         RobotMaster(args.host, args.gripper_port) as gripper:
        for i in range(args.cycles):
            trig = trig_seq[i % len(trig_seq)]
            dt = run_cycle(args.host, args.vision_port, trig, robot, gripper)
            times.append(dt)
            print(f"  사이클 {i + 1}/{args.cycles} ({trig}) 완료 — cycle time {dt:.2f}s")

    print("-" * 40)
    print(f"전체 {len(times)} 사이클 — 평균 {sum(times) / len(times):.2f}s "
          f"(min {min(times):.2f}s / max {max(times):.2f}s)")


if __name__ == "__main__":
    main()
