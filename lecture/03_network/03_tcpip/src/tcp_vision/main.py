"""
03. Ethernet TCP/IP — 로봇 Client(비전 클라이언트) (tcp_vision)

로봇(Client) 역할로 비전(상위) 서버에 접속해 {TRIG} 을 송신하고,
서버가 돌려주는 {X,Y,R} 패킷을 수신·파싱해 콘솔에 출력한다.

HRSS 통신 규약:
  - 패킷은 시작/끝에 중괄호 { } 로 자동 감쌈  ->  TRIG 송신 = 실제 {TRIG} 전송
  - 값은 콤마 , 로 구분                       ->  123.45,67.89,30.0

먼저 별도 터미널에서 검증된 비전 서버를 띄운다:
    python ../../_shared/tcp_echo_server.py --mode vision --port 6000

실행:
    python src/tcp_vision/main.py
    python src/tcp_vision/main.py --host 127.0.0.1 --port 6000
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

import argparse
import socket


def send_packet(sock: socket.socket, payload: str) -> None:
    """HRSS 규약대로 { } 로 감싸 송신한다 (CWRITE 역할)."""
    msg = "{" + payload + "}"
    sock.sendall(msg.encode("ascii"))      # CWRITE(HANDLE, payload)
    print("송신:", msg)


def recv_packet(sock: socket.socket) -> list:
    """서버 응답을 받아 { } 를 벗기고 , 로 분리한다 (CREAD 역할)."""
    data = sock.recv(1024).decode("ascii")  # CREAD(HANDLE, ...)
    body = data.strip().strip("{}")          # { } 제거
    print("수신:", data.strip())
    return body.split(",")                    # , 로 파싱


def main():
    ap = argparse.ArgumentParser(description="로봇 Client — TCP 비전 클라이언트")
    ap.add_argument("--host", default="127.0.0.1",
                    help="비전 서버 IP (실장비라면 앞 3옥텟을 로봇과 일치)")
    ap.add_argument("--port", type=int, default=6000, help="비전 서버 포트")
    args = ap.parse_args()

    print(f"=== TCP 비전 클라이언트 === {args.host}:{args.port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((args.host, args.port))   # COPEN(ETH, HANDLE)
        send_packet(s, "TRIG")               # 촬영 요청
        x, y, r = recv_packet(s)             # 좌표 수신·파싱
        print(f"파싱 결과 -> X={x}, Y={y}, 회전각={r}")
    # with 블록을 벗어나면 소켓이 닫힘 (CCLEAR + 채널 종료 역할)


if __name__ == "__main__":
    main()
