"""
정답 2 — 여러 번 촬영 요청 루프 후 평균/개수 출력

핵심 포인트:
- 같은 연결(소켓) 위에서 {TRIG} 를 N 번 반복 송수신한다 (CWRITE/CREAD 반복).
- 매 응답의 X, Y 를 누적해 마지막에 검출 개수와 평균을 낸다.
- {0.00,0.00,0.0} (검출 없음) 은 평균에서 제외해야 의미 있는 통계가 된다.

흔한 실수:
- 매 요청마다 새 소켓을 열고 닫아 비효율적으로 동작하는 것 (한 연결로 충분).
- 검출 없음(0,0,0) 응답까지 평균에 섞어 값이 깎이는 것.
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

import argparse
import socket


def trig(sock: socket.socket, payload: str):
    """payload 를 { } 로 감싸 송신하고, 응답을 벗겨 (x, y, r) float 로 돌려준다."""
    sock.sendall(("{" + payload + "}").encode("ascii"))   # CWRITE
    data = sock.recv(1024).decode("ascii").strip()        # CREAD
    x, y, r = (float(v) for v in data.strip("{}").split(","))
    return x, y, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=6000)
    ap.add_argument("--count", type=int, default=3, help="촬영 요청 반복 횟수")
    args = ap.parse_args()

    xs, ys = [], []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((args.host, args.port))                 # COPEN(ETH, HANDLE)
        for i in range(1, args.count + 1):
            x, y, r = trig(s, "TRIG")                     # 매 회 촬영 요청
            detected = not (x == 0.0 and y == 0.0 and r == 0.0)
            mark = "검출" if detected else "검출 없음"
            print(f"[{i}/{args.count}] X={x:.2f}, Y={y:.2f}, R={r:.1f}  ({mark})")
            if detected:
                xs.append(x)
                ys.append(y)

    print("-" * 30)
    n = len(xs)
    print(f"요청 {args.count}회 중 검출 {n}회")
    if n:
        print(f"평균 좌표 -> X={sum(xs) / n:.2f}, Y={sum(ys) / n:.2f}")
    else:
        print("검출된 좌표가 없어 평균을 낼 수 없습니다.")


if __name__ == "__main__":
    main()
