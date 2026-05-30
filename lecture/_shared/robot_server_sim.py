"""
robot_server_sim.py  —  로봇 = Modbus SERVER(Slave) 시뮬레이터

매뉴얼 Ch.5.3 (p.41~80). PLC/상위 마스터가 로봇을 제어하는 상황을 PC에서 재현한다.
이 프로그램을 띄워두고, 다른 창에서 modbus_master.py 또는 QModMaster(GUI)로
레지스터를 읽고/쓰며 "명령 사이클"을 실습한다.

  명령 실행 절차(매뉴얼 5.3.3.5):
    1) HR[201] <- 명령번호 (예: 0=PTP, 1=LIN, 3=JOG, 4=GO HOME)
    2) HR[202..] <- 파라미터
    3) HR[200] <- 1  (실행 트리거)
    4) 로봇이 동작 → IR[524](동작상태)가 2(Running)→1(Idle), IR[200]=1(Success)
    5) HR[200] <- 0  (마스터가 리셋, 다음 명령 준비)

  ※ 본 시뮬레이터의 파라미터 배치는 학습용으로 단순화했다(아래 PTP 주석 참고).
    실제 로봇의 전체 파라미터 표는 매뉴얼 Table 16 참조.

레지스터 요약 (zero_mode, 주소는 0-base):
  Discrete Input (읽기전용) : 0~ SO1..SOn (SO1=Run, SO2=Held, SO3=Fault, SO4=Ready ...)
  Coil           (읽기/쓰기): 0~ SI1..SIn (SI1=Start, SI2=Hold, SI3=Stop, SI4=Enable ...),
                              300~ DO1..DOn
  Input Register (읽기전용) : 100 속도%, 200 명령상태, 201 현재명령, 300~ 관절 A1..A6(L/H),
                              400~ 직교 X..C(L/H), 524 동작상태(1 Idle/2 Run/3 Hold)
  Holding Reg    (읽기/쓰기): 100 속도설정, 200 실행트리거, 201 명령번호, 202~ 파라미터

실행:  python robot_server_sim.py            # 0.0.0.0:502, Slave ID 1
       python robot_server_sim.py --port 1502 --unit 1
종료:  Ctrl+C
"""
import argparse
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from word_tools import split_word, combine_word  # noqa: E402

from pymodbus.datastore import (  # noqa: E402
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartTcpServer  # noqa: E402

# Modbus 함수코드를 레지스터 종류 선택자로 사용 (pymodbus 관례)
CO, DI, HR, IR = 1, 2, 3, 4

CMD_NAMES = {0: "PTP", 1: "LIN", 2: "CIRC", 3: "JOG", 4: "GO HOME", 5: "T_STOP", 6: "STOP"}


class RobotLogic(threading.Thread):
    """백그라운드에서 명령 트리거를 감시하고 가상 로봇을 동작시킨다."""

    def __init__(self, context, unit=1, period=0.05):
        super().__init__(daemon=True)
        self.ctx = context[unit if not context.single else 0]
        self.period = period
        self.busy = False
        self.ack_wait = False     # 마스터가 HR[200]=0 으로 리셋하기를 대기
        self.ticks = 0
        self.move_ticks = 10      # 약 0.5초 가상 이동 시간
        self._init_registers()

    def _init_registers(self):
        # SO 기본 상태: SO4=Ready ON
        self.ctx.setValues(DI, 0, [0, 0, 0, 1, 0, 0, 0, 0])
        # IR 상태 초기화
        self.ctx.setValues(IR, 100, [100])        # 속도 100%
        self.ctx.setValues(IR, 200, [0, 0])       # 명령상태=0, 현재명령=0
        self.ctx.setValues(IR, 524, [1])          # 동작상태=Idle
        self.ctx.setValues(IR, 522, [1])          # 모터 여자 ON
        # 현재 위치(관절/직교) 0 으로
        self.ctx.setValues(IR, 300, [0] * 12)
        self.ctx.setValues(IR, 400, [0] * 12)

    # --- 헬퍼 -------------------------------------------------------------
    def _get(self, fc, addr, count=1):
        return self.ctx.getValues(fc, addr, count=count)

    def _set(self, fc, addr, values):
        self.ctx.setValues(fc, addr, values)

    def _set_so(self, idx, on):
        self._set(DI, idx, [1 if on else 0])

    # --- 명령 실행 --------------------------------------------------------
    def _start_command(self):
        cmd = self._get(HR, 201)[0]
        self.current_cmd = cmd
        self.busy = True
        self.ticks = 0
        self._set(IR, 524, [2])         # Running
        self._set(IR, 201, [cmd])       # 현재 명령
        self._set(IR, 200, [0])         # 상태 진행중
        self._set_so(0, 1)              # SO1=Run ON
        print(f"  ▶ 명령 시작: {cmd} ({CMD_NAMES.get(cmd, '?')})")

    def _finish_command(self):
        cmd = self.current_cmd
        params = self._get(HR, 200, count=20)   # HR[200..219]
        # params[0]=trigger, [1]=명령번호, [2]=타입, [3..14]=6축 L/H, [15]=속도 ...
        if cmd in (0, 1):                        # PTP / LIN
            mtype = params[2]                    # 0=Joint, 1=Cartesian
            axis_words = params[3:15]            # 12워드 = 6축(L,H)
            target = self.ctx_in_eng(axis_words)
            if mtype == 0:
                self._set(IR, 300, axis_words)   # 현재 관절 위치 = 목표
                print(f"     관절 이동 완료 A1~A6 = {target}")
            else:
                self._set(IR, 400, axis_words)   # 현재 직교 위치 = 목표
                print(f"     직교 이동 완료 X..C = {target}")
            spd = params[15] if params[15] else 100
            self._set(IR, 100, [spd])
        elif cmd == 4:                           # GO HOME
            self._set(IR, 300, [0] * 12)
            self._set(IR, 400, [0] * 12)
            print("     원점 복귀 완료")
        # 공통 마무리
        self._set(IR, 524, [1])         # Idle
        self._set(IR, 200, [1])         # Success
        self._set_so(0, 0)              # SO1=Run OFF
        self.busy = False
        self.ack_wait = True
        print(f"  ✔ 명령 완료: IR[200]=1(Success). 마스터는 HR[200]<-0 으로 리셋하세요.")

    @staticmethod
    def ctx_in_eng(words):
        """[L,H,L,H,...] 12워드 -> 6개 공학값(0.001 스케일) 리스트."""
        out = []
        for i in range(0, 12, 2):
            low = words[i] if words[i] < 32768 else words[i] - 65536
            high = words[i + 1] if words[i + 1] < 32768 else words[i + 1] - 65536
            out.append(round(combine_word(low, high) * 0.001, 3))
        return out

    # --- 메인 루프 --------------------------------------------------------
    def run(self):
        print("로봇 로직 스레드 시작.")
        while True:
            trig = self._get(HR, 200)[0]
            if self.ack_wait:
                if trig == 0:
                    self.ack_wait = False     # 마스터 리셋 확인 → 다음 명령 가능
            elif self.busy:
                self.ticks += 1
                if self.ticks >= self.move_ticks:
                    self._finish_command()
            elif trig == 1:
                self._start_command()
            time.sleep(self.period)


def build_context():
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * 600),
        co=ModbusSequentialDataBlock(0, [0] * 600),
        hr=ModbusSequentialDataBlock(0, [0] * 2100),
        ir=ModbusSequentialDataBlock(0, [0] * 600),
        zero_mode=True,
    )
    return ModbusServerContext(slaves=store, single=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    args = ap.parse_args()

    # Windows 기본 콘솔(cp949)에서 ▶/✔ 출력 시 UnicodeEncodeError 로
    # 로직 스레드가 죽는 것을 방지 (PYTHONUTF8 미설정 환경 대비)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    context = build_context()
    logic = RobotLogic(context, unit=args.unit)
    logic.start()

    print("=" * 60)
    print(f" 로봇 Modbus SERVER 시뮬레이터  {args.host}:{args.port}  (Slave ID {args.unit})")
    print(" 마스터(modbus_master.py / QModMaster)로 접속해 명령 사이클을 실습하세요.")
    print(" 종료: Ctrl+C")
    print("=" * 60)
    try:
        StartTcpServer(context=context, address=(args.host, args.port))
    except KeyboardInterrupt:
        print("\n서버 종료.")


if __name__ == "__main__":
    main()
