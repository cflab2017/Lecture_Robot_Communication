"""
modbus_master.py  —  Modbus 마스터(Client) 실습 도구

두 가지 용도로 사용한다.
  (1) 명령행 CLI : 시뮬레이터(슬레이브)의 레지스터를 직접 읽고/쓰며 4종 데이터 타입을 익힘
  (2) import 모듈 : 다른 실습 스크립트에서 RobotMaster 클래스를 가져다 사용

pymodbus 3.6.x 기준. 설치:  python -m pip install pymodbus==3.6.9

CLI 예시:
    # 로봇 서버 시뮬레이터(robot_server_sim.py)가 502 포트에서 돌고 있다고 가정
    python modbus_master.py read-hr 100 1          # 속도 설정값 읽기
    python modbus_master.py write-hr 100 50         # 속도 50% 로 쓰기
    python modbus_master.py read-ir 524 1           # 동작 상태 읽기
    python modbus_master.py read-di 0 8             # SO1~SO8 상태
    python modbus_master.py write-coil 0 1          # SI1(Start) 트리거
    python modbus_master.py read-coil 0 8
"""
import argparse
import sys

from pymodbus.client import ModbusTcpClient


class RobotMaster:
    """로봇/슬레이브를 제어하는 Modbus TCP 마스터 래퍼."""

    def __init__(self, host="127.0.0.1", port=502, unit=1):
        self.client = ModbusTcpClient(host, port=port)
        self.unit = unit

    def __enter__(self):
        if not self.client.connect():
            raise ConnectionError(f"슬레이브에 연결 실패: {self.client}")
        return self

    def __exit__(self, *exc):
        self.client.close()

    # --- 읽기 -------------------------------------------------------------
    def read_holding(self, addr, count=1):
        rr = self.client.read_holding_registers(addr, count=count, slave=self.unit)
        self._check(rr)
        return rr.registers

    def read_input(self, addr, count=1):
        rr = self.client.read_input_registers(addr, count=count, slave=self.unit)
        self._check(rr)
        return rr.registers

    def read_coils(self, addr, count=1):
        rr = self.client.read_coils(addr, count=count, slave=self.unit)
        self._check(rr)
        return rr.bits[:count]

    def read_discrete(self, addr, count=1):
        rr = self.client.read_discrete_inputs(addr, count=count, slave=self.unit)
        self._check(rr)
        return rr.bits[:count]

    # --- 쓰기 -------------------------------------------------------------
    def write_holding(self, addr, values):
        if isinstance(values, int):
            values = [values]
        # Modbus 레지스터는 16bit unsigned 로 전송된다. split_word() 가 돌려주는
        # 음수 word(예: High=-5)도 그대로 받아 0~65535 로 인코딩한다(& 0xFFFF).
        # 슬레이브가 다시 부호 있는 값으로 해석한다.
        values = [v & 0xFFFF for v in values]
        rr = self.client.write_registers(addr, values, slave=self.unit)
        self._check(rr)

    def write_coil(self, addr, value):
        rr = self.client.write_coil(addr, bool(value), slave=self.unit)
        self._check(rr)

    def write_coils(self, addr, values):
        rr = self.client.write_coils(addr, [bool(v) for v in values], slave=self.unit)
        self._check(rr)

    @staticmethod
    def _check(rr):
        if rr.isError():
            raise IOError(f"Modbus 오류 응답: {rr}")


def main():
    ap = argparse.ArgumentParser(description="Modbus TCP 마스터 CLI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1, help="Slave ID")
    ap.add_argument("op", choices=[
        "read-hr", "write-hr", "read-ir",
        "read-coil", "write-coil", "read-di",
    ])
    ap.add_argument("addr", type=int)
    ap.add_argument("value", type=int, nargs="?", default=1,
                    help="read 계열은 개수(count), write 계열은 쓸 값")
    args = ap.parse_args()

    try:
        with RobotMaster(args.host, args.port, args.unit) as m:
            if args.op == "read-hr":
                print(m.read_holding(args.addr, args.value))
            elif args.op == "write-hr":
                m.write_holding(args.addr, args.value)
                print(f"HR[{args.addr}] <- {args.value}  완료")
            elif args.op == "read-ir":
                print(m.read_input(args.addr, args.value))
            elif args.op == "read-coil":
                print([int(b) for b in m.read_coils(args.addr, args.value)])
            elif args.op == "write-coil":
                m.write_coil(args.addr, args.value)
                print(f"Coil[{args.addr}] <- {bool(args.value)}  완료")
            elif args.op == "read-di":
                print([int(b) for b in m.read_discrete(args.addr, args.value)])
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
