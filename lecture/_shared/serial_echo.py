"""serial_echo.py — RS-232 에코 서버 (PC 시뮬레이션, 03-rs232 챕터)

com0com 가상 COM 포트 쌍(예: COM5 <-> COM6)에서 한쪽(COM6)을 열고,
수신한 데이터를 HIWIN 패킷 포맷처럼 중괄호 { } 로 감싸 되돌려 보냅니다.
실제 로봇의 RS-232 응답 흐름(상위 시스템 역할)을 PC에서 흉내 냅니다.

실행:
    python serial_echo.py --port COM6 --baud 9600
중지: Ctrl+C
"""

import argparse
import serial  # pyserial


def main():
    ap = argparse.ArgumentParser(description="RS-232 에코 서버 (시리얼 수신 -> {data} 응답)")
    ap.add_argument("--port", default="COM6", help="열 가상 COM 포트 (기본 COM6)")
    ap.add_argument("--baud", type=int, default=9600, help="baud rate (양쪽 동일해야 함)")
    args = ap.parse_args()

    # timeout=1: read()가 데이터를 1초까지만 기다리도록 해 무한 대기를 막음
    ser = serial.Serial(args.port, args.baud, timeout=1)
    print(f"[echo] {args.port} @ {args.baud}bps 열림. 수신 대기 중... (Ctrl+C 종료)")
    try:
        while True:
            data = ser.read(64)          # 최대 64바이트 수신 (없으면 1초 후 b'')
            if not data:
                continue
            text = data.decode("ascii", errors="replace")
            reply = "{" + text + "}"      # HIWIN 패킷 포맷처럼 { } 로 감쌈
            ser.write(reply.encode("ascii"))
            print(f"[echo] 수신 {data!r} -> 응답 {reply!r}")
    except KeyboardInterrupt:
        print("\n[echo] 종료")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
