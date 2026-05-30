"""
gripper_sim.py  —  XEG 전동 그리퍼 = Modbus SERVER(Slave) 시뮬레이터

매뉴얼 5.4.5.1 (p.106~111). 로봇이 Modbus CLIENT(마스터)가 되어 그리퍼를 제어하는
상황에서, '그리퍼' 역할을 PC가 대신한다. 로봇 대신 modbus_master.py 로 제어해 본다.

레지스터 맵 (XEG-64 기준, 10진 주소, zero_mode):
  Holding Register (쓰기)
    1536  그리퍼 모델            (2624 = XEG-64)
    1552  HOME 리셋             (1 쓰면 원점화)
    1600  방향                  (0=닫기 / 1=열기)
    1601  이동 행정 [0.01mm]
    1602  이동 속도 [0.01mm/s]
    1603  그립 행정 [0.01mm]
    1604  그립 속도 [0.01mm/s]
    1605  그립 힘   [%]
    1606  설정 확정/실행        (1 쓰면 동작 시작 → 완료 후 0 으로 자동 복귀)
  Input Register (읽기)
    769 (0x301)  그리퍼 상태     (0 Idle,1 Busy,2 Pos도달,3 Hold,4~7 Alarm)
    770          현재 위치 [0.01mm]
    771 (0x303)  펌웨어 버전 major
    772 (0x304)  펌웨어 버전 minor

실행:  python gripper_sim.py            # 0.0.0.0:502 (로봇 서버와 동시에 띄울 땐 포트 분리)
       python gripper_sim.py --port 1503
종료:  Ctrl+C
"""
import argparse
import sys
import threading
import time

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartTcpServer

CO, DI, HR, IR = 1, 2, 3, 4

ST_IDLE, ST_BUSY, ST_POS, ST_HOLD = 0, 1, 2, 3
REG_STATUS = 769
REG_CUR_POS = 770


class GripperLogic(threading.Thread):
    def __init__(self, context, period=0.05):
        super().__init__(daemon=True)
        self.ctx = context[0]
        self.period = period
        self.busy = False
        self.ticks = 0
        self.move_ticks = 8
        # 초기값: 모델, 펌웨어, 상태 Idle
        self.ctx.setValues(HR, 1536, [2624])
        self.ctx.setValues(IR, REG_STATUS, [ST_IDLE])
        self.ctx.setValues(IR, REG_CUR_POS, [0])
        self.ctx.setValues(IR, 771, [1, 0])     # FW 1.0

    def run(self):
        print("그리퍼 로직 스레드 시작.")
        while True:
            confirm = self.ctx.getValues(HR, 1606, count=1)[0]
            if not self.busy and confirm == 1:
                direction = self.ctx.getValues(HR, 1600, count=1)[0]
                stroke = self.ctx.getValues(HR, 1601, count=1)[0]
                self.busy = True
                self.ticks = 0
                self.target = stroke if direction == 1 else 0
                self.ctx.setValues(IR, REG_STATUS, [ST_BUSY])
                print(f"  ▶ 그리퍼 {'열기' if direction == 1 else '닫기'} "
                      f"(목표 {self.target/100:.2f} mm)")
            elif self.busy:
                self.ticks += 1
                if self.ticks >= self.move_ticks:
                    self.ctx.setValues(IR, REG_CUR_POS, [self.target])
                    self.ctx.setValues(IR, REG_STATUS, [ST_POS])
                    self.ctx.setValues(HR, 1606, [0])   # 확정 플래그 자동 리셋
                    self.busy = False
                    print(f"  ✔ 동작 완료: 상태=2(Pos), 위치={self.target/100:.2f} mm")
            time.sleep(self.period)


def build_context():
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * 100),
        co=ModbusSequentialDataBlock(0, [0] * 100),
        hr=ModbusSequentialDataBlock(0, [0] * 1700),
        ir=ModbusSequentialDataBlock(0, [0] * 800),
        zero_mode=True,
    )
    return ModbusServerContext(slaves=store, single=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=502)
    args = ap.parse_args()

    # cp949 콘솔에서 ▶/✔ 출력 시 로직 스레드가 죽는 것을 방지
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    context = build_context()
    GripperLogic(context).start()
    print("=" * 60)
    print(f" XEG 그리퍼 Modbus SERVER 시뮬레이터  {args.host}:{args.port}")
    print(" 로봇(Client) 대신 modbus_master.py 로 1600/1601/1606 을 써서 제어해 보세요.")
    print(" 종료: Ctrl+C")
    print("=" * 60)
    try:
        StartTcpServer(context=context, address=(args.host, args.port))
    except KeyboardInterrupt:
        print("\n서버 종료.")


if __name__ == "__main__":
    main()
