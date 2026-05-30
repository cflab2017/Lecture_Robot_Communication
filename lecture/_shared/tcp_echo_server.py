"""
tcp_echo_server.py  —  Ethernet TCP/IP 통신 실습용 상위 시스템(비전) 시뮬레이터

매뉴얼 Ch.3 (p.30~33). 로봇은 Client, 비전/상위 시스템은 Server 로 동작한다.
HRSS 통신 규약에 맞춰 패킷을 중괄호 { } 로 감싸고 콤마 , 로 구분한다.

  로봇이 보냄:   {TRIG}            (촬영 요청)
  서버가 응답:   {123.45,67.89,30.0}   (X, Y, 회전각)

실행:
    python tcp_echo_server.py                 # 비전 모드, 0.0.0.0:6000
    python tcp_echo_server.py --mode echo      # 받은 값을 그대로 되돌려줌
    python tcp_echo_server.py --port 6000 --host 0.0.0.0

종료: Ctrl+C
"""
import argparse
import socket


def make_vision_reply(request: str) -> str:
    """간단한 가짜 비전 결과. 실제로는 카메라가 검출한 좌표가 들어간다."""
    # 요청 텍스트(예: TRIG, COUNT 등)에 따라 다른 좌표를 줄 수도 있다.
    samples = {
        "TRIG":  "123.45,67.89,30.0",
        "TRIG2": "-45.10,210.00,-15.0",
    }
    return samples.get(request.strip(), "0.00,0.00,0.0")


def handle(conn: socket.socket, addr, mode: str):
    print(f"[연결] {addr} 접속")
    with conn:
        buf = ""
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buf += data.decode("ascii", errors="replace")
            # 패킷 종료 기호 '}' 단위로 처리
            while "}" in buf:
                pkt, buf = buf.split("}", 1)
                payload = pkt.replace("{", "").strip()
                print(f"  수신: {{{payload}}}")
                if mode == "echo":
                    reply = payload
                else:
                    reply = make_vision_reply(payload)
                msg = "{" + reply + "}"
                conn.sendall(msg.encode("ascii"))
                print(f"  송신: {msg}")
    print(f"[종료] {addr}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=6000)
    ap.add_argument("--mode", choices=["vision", "echo"], default="vision")
    args = ap.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((args.host, args.port))
        srv.listen(1)
        print(f"TCP 서버 대기 중  {args.host}:{args.port}  (mode={args.mode})")
        print("로봇(Client)의 COPEN(ETH, ...) 접속을 기다립니다.  종료: Ctrl+C")
        try:
            while True:
                conn, addr = srv.accept()
                handle(conn, addr, args.mode)
        except KeyboardInterrupt:
            print("\n서버를 종료합니다.")


if __name__ == "__main__":
    main()
