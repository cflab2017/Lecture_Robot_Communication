"""
02. I/O 통신 — 픽앤플레이스 I/O 핸드셰이크 상태기계 (io_handshake)

로봇이 $DO[6]로 그리퍼 동작을 출력하면, 상위 PLC가 잠시 뒤 $DI로 응답하는
핸드셰이크 흐름을 콘솔에 단계별로 출력한다. 실제 물리 I/O(CN6 단자대 전압) 대신
파이썬 딕셔너리로 신호 상태를 흉내 내며, 표준 라이브러리만 사용한다.
(시뮬레이터/시리얼 포트 불필요. _shared 부트스트랩은 트랙 일관성을 위해 둔다.)

핸드셰이크 정의:
    $DO[6]=TRUE  -> 그리퍼 CLOSE(집기) 지령,  PLC가 $DI[1]=TRUE(그립완료)로 응답
    $DO[6]=FALSE -> 그리퍼 OPEN(놓기)  지령,  PLC가 $DI[4]=TRUE(언그립완료)로 응답

실행:  python src/io_handshake/main.py
"""
import os
import sys
import time

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

# 물리 I/O를 흉내 내는 신호 테이블 (실제로는 CN6 단자대의 전압 ON/OFF)
DO = {6: False}            # 로봇 출력: $DO[6] = 그리퍼 CLOSE/OPEN 지령
DI = {1: False, 4: False}  # 로봇 입력: $DI[1]=그립완료, $DI[4]=언그립완료

# 데모 속도(초). 0으로 두면 즉시 진행한다.
RESPOND_DELAY = 1.0
POLL_INTERVAL = 0.05


def plc_respond(do_pin, di_pin, delay=RESPOND_DELAY):
    """상위 PLC 역할: 로봇의 $DO 변화를 보고 delay 뒤 $DI로 응답한다."""
    level = "ON" if DO[do_pin] else "OFF"
    print(f"   [PLC ] $DO[{do_pin}]={level} 감지 → 액추에이터 동작 중...")
    time.sleep(delay)
    DI[di_pin] = True
    print(f"   [PLC ] 동작 완료 → $DI[{di_pin}]=TRUE 응답")


def robot_wait_for(di_pin):
    """로봇 명령 WAIT FOR $DI[n]==TRUE 를 흉내 낸다 (응답 올 때까지 블로킹 대기)."""
    print(f"   [ROBO] WAIT FOR $DI[{di_pin}]==TRUE ...")
    while not DI[di_pin]:
        time.sleep(POLL_INTERVAL)
    print(f"   [ROBO] $DI[{di_pin}]==TRUE 확인 → 다음 동작 진행\n")


def robot_set_do(do_pin, value, note=""):
    """로봇 명령 $DO[n]=TRUE/FALSE 를 흉내 낸다 (출력 비트 ON/OFF)."""
    DO[do_pin] = value
    level = "TRUE" if value else "FALSE"
    tail = f" ({note})" if note else ""
    print(f"   [ROBO] $DO[{do_pin}]={level} 출력{tail}")


def handshake(title, do_pin, do_value, di_pin, note=""):
    """$DO 출력 → PLC 응답 → WAIT FOR $DI 라는 한 번의 핸드셰이크."""
    print(f"== {title} ==")
    robot_set_do(do_pin, do_value, note)
    plc_respond(do_pin, di_pin)   # 실제로는 PLC가 별도 장치에서 동시 동작
    robot_wait_for(di_pin)


def main():
    print("픽앤플레이스 I/O 핸드셰이크 시뮬레이션 시작\n")

    # ① GRIP: $DO[6] ON → $DI[1] 그립완료
    handshake("GRIP (집기): $DO[6] ON, $DI[1] 그립완료 대기",
              do_pin=6, do_value=True, di_pin=1)

    # ② UNGRIP: $DO[6] OFF → $DI[4] 언그립완료
    handshake("UNGRIP (놓기): $DO[6] OFF, $DI[4] 언그립완료 대기",
              do_pin=6, do_value=False, di_pin=4, note="그리퍼 OPEN")

    print("사이클 완료 ✅  (모든 핸드셰이크 정상 종료)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
