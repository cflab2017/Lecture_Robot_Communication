"""serial_client.py — RS-232 로봇 클라이언트 (PC 시뮬레이션, 03-rs232 챕터)

com0com 가상 COM 포트 쌍의 반대쪽(COM5)을 열어 패킷을 전송하고
에코 서버(serial_echo.py, COM6)의 응답을 받아 출력합니다.
실제 로봇에서는 이 흐름을 COPEN(SER,HANDLE) -> CWRITE -> CREAD 로 작성합니다.

실행 (다른 터미널에서 serial_echo.py 가 떠 있어야 함):
    python serial_client.py --port COM5 --baud 9600 --value 123
"""

import argparse
import serial  # pyserial


def main():
    ap = argparse.ArgumentParser(description="RS-232 클라이언트 (패킷 전송 후 응답 수신)")
    ap.add_argument("--port", default="COM5", help="열 가상 COM 포트 (기본 COM5)")
    ap.add_argument("--baud", type=int, default=9600, help="baud rate (양쪽 동일해야 함)")
    ap.add_argument("--value", default="123", help="전송할 값 (기본 123)")
    args = ap.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=1)

    packet = ("{" + args.value + "}").encode("ascii")   # 예: b'{123}'
    ser.write(packet)
    print(f"[client] {args.port} @ {args.baud}bps -> 송신 {packet!r}")

    resp = ser.read(64)                                  # 에코 서버 응답 수신
    print(f"[client] 수신 {resp!r}  (decode: {resp.decode('ascii', errors='replace')})")

    ser.close()


if __name__ == "__main__":
    main()
