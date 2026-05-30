"""
정답 1 — 3스테이션 연속 핸드셰이크

핵심 포인트:
- 1편 main.py 의 단일 핸드셰이크(GRIP/UNGRIP)를 여러 스테이션의 반복으로 일반화한다.
- 각 스테이션은 (이름, $DO핀, $DO값, $DI핀) 4요소로 표현되며, 데이터(리스트)로 두면
  스테이션을 추가/삭제하기 쉽다 — 동작 흐름과 데이터를 분리하는 패턴.
- 이전 응답($DI)을 초기화해야 다음 WAIT FOR 가 즉시 통과하지 않는다.

흔한 실수:
- DI 비트를 리셋하지 않아 다음 핸드셰이크가 대기 없이 바로 통과하는 것.
- 출력 메시지에서 $DO ON/OFF 와 $DI 핀 번호를 혼동하는 것.

표준 라이브러리만 사용. 시뮬레이터/포트 불필요.
실행:  python main.py
"""
import os
import sys
import time

# _shared 공유 라이브러리 경로 추가 (깊이 무관하게 상위에서 _shared 탐색)
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "_shared")):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, "_shared"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DELAY = 0.3  # PLC 응답 지연(초). 0으로 두면 즉시 진행.

# 신호 테이블 (물리 I/O 흉내)
DO = {6: False}
DI = {1: False, 4: False}

# 3스테이션 시퀀스: (제목, $DO핀, $DO값, $DI응답핀)
STATIONS = [
    ("ST1 PICK  (집기) : $DO[6] ON,  $DI[1] 그립완료 대기",   6, True,  1),
    ("ST2 PLACE (놓기) : $DO[6] OFF, $DI[4] 언그립완료 대기", 6, False, 4),
    ("ST3 PICK  (집기) : $DO[6] ON,  $DI[1] 그립완료 대기",   6, True,  1),
]


def handshake(idx, title, do_pin, do_value, di_pin):
    print(f"[{idx}] == {title} ==")
    DO[do_pin] = do_value
    DI[di_pin] = False  # 이전 응답 초기화 → 이번 WAIT FOR 가 실제로 대기하도록
    level = "TRUE" if do_value else "FALSE"
    print(f"    [ROBO] $DO[{do_pin}]={level} 출력")
    # PLC 응답
    print(f"    [PLC ] $DO[{do_pin}]={'ON' if do_value else 'OFF'} 감지 → 동작 중...")
    time.sleep(DELAY)
    DI[di_pin] = True
    print(f"    [PLC ] 동작 완료 → $DI[{di_pin}]=TRUE 응답")
    # 로봇 대기
    print(f"    [ROBO] WAIT FOR $DI[{di_pin}]==TRUE ...")
    while not DI[di_pin]:
        time.sleep(0.05)
    print(f"    [ROBO] $DI[{di_pin}]==TRUE 확인 → 다음 동작 진행\n")


def main():
    print("3스테이션 연속 I/O 핸드셰이크 시작\n")
    for i, (title, do_pin, do_value, di_pin) in enumerate(STATIONS, start=1):
        handshake(i, title, do_pin, do_value, di_pin)
    print(f"전체 {len(STATIONS)}스테이션 완료 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
