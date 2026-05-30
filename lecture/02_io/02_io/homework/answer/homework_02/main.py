"""
정답 2 — 핸드셰이크 타임아웃 감시

핵심 포인트:
- 실제 현장에서 $DI 응답이 영영 오지 않으면(케이블 탈락·PLC 멈춤 등) WAIT FOR 는
  무한 대기한다. 그래서 "기한(timeout)"을 두고 그 안에 응답이 없으면 경고를 낸다.
- 경과 시간은 time.monotonic() 으로 측정한다(시스템 시계 변경에 영향받지 않음).
- 정상 케이스와 타임아웃 케이스를 모두 보여준다.

흔한 실수:
- time.time() 대신 sleep 횟수로만 시간을 세어 부정확해지는 것.
- 타임아웃 후에도 계속 진행해 잘못된 동작을 이어가는 것 → 여기서는 경고만 내고
  해당 스텝을 실패로 처리한다.

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

DI = {1: False, 4: False}
TIMEOUT = 2.0      # 응답을 기다릴 최대 시간(초)
POLL = 0.05


def wait_for_di(di_pin, respond_after):
    """
    $DI[di_pin] 응답을 TIMEOUT 안에서 기다린다.
    respond_after 초 뒤에 PLC가 응답한다고 가정(None이면 끝내 응답하지 않음).
    응답을 받으면 True, 타임아웃이면 False 를 반환한다.
    """
    print(f"   [ROBO] WAIT FOR $DI[{di_pin}]==TRUE ... (timeout {TIMEOUT:.1f}s)")
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        # PLC가 respond_after 시점에 응답했다고 모사
        if respond_after is not None and elapsed >= respond_after:
            DI[di_pin] = True
        if DI[di_pin]:
            print(f"   [ROBO] $DI[{di_pin}]==TRUE 확인 ({elapsed:.2f}s) → 진행\n")
            return True
        if elapsed >= TIMEOUT:
            print(f"   [WARN] ⚠️  $DI[{di_pin}] 응답 없음 — {TIMEOUT:.1f}s 타임아웃! "
                  f"(케이블/PLC 점검 필요)\n")
            return False
        time.sleep(POLL)


def main():
    print("핸드셰이크 타임아웃 감시 데모 시작\n")

    # 케이스 A: 정상 — PLC가 0.5s 뒤 응답
    print("== CASE A: 정상 응답 ($DO[6] ON → $DI[1]) ==")
    print("   [ROBO] $DO[6]=TRUE 출력")
    ok_a = wait_for_di(1, respond_after=0.5)

    # 케이스 B: 고장 — PLC가 끝내 응답하지 않음
    print("== CASE B: 무응답 ($DO[6] OFF → $DI[4]) ==")
    print("   [ROBO] $DO[6]=FALSE 출력")
    ok_b = wait_for_di(4, respond_after=None)

    print(f"결과: CASE A={'OK' if ok_a else 'TIMEOUT'}, "
          f"CASE B={'OK' if ok_b else 'TIMEOUT'}")
    print("정상 종료 ✅" if ok_a and ok_b else "타임아웃 발생 ❌ — 위 ⚠️ 항목 점검")
    return 0 if (ok_a and ok_b) else 1


if __name__ == "__main__":
    sys.exit(main())
