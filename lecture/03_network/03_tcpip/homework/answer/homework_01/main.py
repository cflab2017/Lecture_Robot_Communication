"""
정답 1 — TRIG2 음수 좌표 처리·표시

핵심 포인트:
- {TRIG2} 를 보내면 서버가 {-45.10,210.00,-15.0} 처럼 음수가 섞인 좌표를 준다.
- 파싱 결과는 문자열이므로 float() 로 변환해야 부호·소수 계산이 가능하다.
- 음수 좌표를 부호(+/-) 정렬로 보기 좋게 출력한다.

흔한 실수:
- { } 를 벗기지 않고 split 해 첫/마지막 값에 중괄호가 붙는 것.
- float 변환 없이 문자열을 그대로 비교/계산하려는 것.
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
    body = data.strip("{}")
    x, y, r = (float(v) for v in body.split(","))
    return data, x, y, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=6000)
    args = ap.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((args.host, args.port))                 # COPEN(ETH, HANDLE)
        raw, x, y, r = trig(s, "TRIG2")                   # 2번 부품 요청
        print(f"송신: {{TRIG2}}")
        print(f"수신: {raw}")
        sign = "음수 좌표 포함" if (x < 0 or y < 0 or r < 0) else "모두 양수"
        print(f"파싱 결과 -> X={x:+.2f}, Y={y:+.2f}, 회전각={r:+.1f}  ({sign})")


if __name__ == "__main__":
    main()
