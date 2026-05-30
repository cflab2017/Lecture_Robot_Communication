# 09. 종합 실습 — 비전·로봇·그리퍼 자동화 셀

이 트랙의 마지막 편입니다. 지금까지 따로 배운 통신 조각들 — [03편](../../03_network/03_tcpip/README.md) TCP/IP, [06편](../../05_server/06_modbus_server/README.md) 로봇=Server 명령 사이클, [07편](../../06_client/07_modbus_client/README.md) 로봇=Client 그리퍼 제어, [08편](../../07_debug/08_monitoring/README.md) 모니터링 — 을 **하나의 자동화 셀** 로 묶습니다. 상위 **비전 시스템** 이 부품 위치를 알려주면(TCP/IP), **로봇** 이 그 좌표로 이동(Modbus)해 **그리퍼** 로 집고, 지정 위치에 놓고 **원점 복귀** 하는 — 현장에서 가장 흔한 **픽앤플레이스(Pick & Place)** 셀을 PC 한 대로 완성합니다.

## 학습 목표
- 서로 다른 3개 역할(비전=TCP Server, 로봇=Modbus Slave, 그리퍼=Modbus Slave)을 한 컨트롤러에서 **동시에** 다룬다.
- 비전이 준 실수 좌표를 `split_word()` 로 인코딩해 로봇의 **직교(Cartesian) LIN 명령 사이클** 로 보낸다(음수 좌표 포함).
- 로봇 명령 사이클과 그리퍼 사이클을 **상태 폴링으로 직렬화** 해 안전하게 연결한다(상태 잔상/latch 회피).
- 비전 수신 → 픽(2단 Z) → 집기 → 플레이스 → 놓기 → 원점 복귀의 **전체 사이클** 을 오케스트레이션하고 **사이클 타임** 을 측정한다.

## 🏭 시나리오 개요

**셀 제어기(`cell_controller`)** 가 지휘자입니다. 비전에게는 **TCP Client** 로 접속하고, 로봇·그리퍼에게는 **Modbus Master** 로 명령합니다.

```
                 ┌──────────────────────────────────────────────┐
                 │     cell_controller (셀 제어기 / 이번 편)     │
                 │  = 03편 TCP Client + 06/07편 Modbus Master    │
                 └────┬──────────────┬─────────────────┬─────────┘
      (1) TCP/IP      │  (2) Modbus  │    (3) Modbus    │
       {TRIG}         │  명령 사이클 │    열기/닫기      │
       {X,Y,R}        ▼              ▼                  ▼
     ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
     │  비전 시스템    │ │  로봇 (Slave)   │ │  그리퍼 (Slave) │
     │ tcp_echo_server│ │robot_server_sim│ │  gripper_sim   │
     │   TCP :6000     │ │  Modbus :1502   │ │  Modbus :1503   │
     └────────────────┘ └────────────────┘ └────────────────┘

   동작 순서 (한 사이클):
   ① 비전에 {TRIG} 송신 → {X, Y, R} 수신            (TCP/IP, 03편)
   ② 로봇 LIN 이동: (X,Y, 접근Z) → (X,Y, 픽Z)        (Modbus, 06편)
   ③ 그리퍼 닫기 = 부품 집기                          (Modbus, 07편)
   ④ 로봇 LIN 이동: 픽 상승 → 플레이스 위치           (Modbus, 06편)
   ⑤ 그리퍼 열기 = 부품 놓기                          (Modbus, 07편)
   ⑥ 로봇 GO HOME = 원점 복귀                         (Modbus, 06편)
```

> **역할 헷갈림 주의** — 비전은 로봇 관점에선 Server지만, 이번 셀에서는 `cell_controller` 가 비전에 **접속하는 Client** 입니다([03편](../../03_network/03_tcpip/README.md)에서 로봇이 `COPEN` 으로 비전에 접속한 것과 같은 구도). 로봇·그리퍼에 대해서는 컨트롤러가 **Modbus Master** 입니다. "누가 먼저 말을 거는가" 로 구분하세요.

## 대상 환경
- 도구: Python 3.10+ / pymodbus 3.6.9 / pyserial 3.5
- 플랫폼: Windows PC (시뮬레이션) — 실제 로봇/카메라/그리퍼 불필요
- 검증: 터미널 4개 — 시뮬레이터 3개 + `python src/cell_controller/main.py`

## 실습 준비물

| 항목 | 내용 |
|------|------|
| 비전(Server) | [`../../_shared/tcp_echo_server.py`](../../_shared/tcp_echo_server.py) — 상위 비전 시스템 (TCP **6000**) |
| 로봇(Slave) | [`../../_shared/robot_server_sim.py`](../../_shared/robot_server_sim.py) — 로봇 = Modbus Server (포트 **1502**) |
| 그리퍼(Slave) | [`../../_shared/gripper_sim.py`](../../_shared/gripper_sim.py) — XEG 그리퍼 = Modbus Server (포트 **1503**) |
| 보조 모듈 | [`../../_shared/modbus_master.py`](../../_shared/modbus_master.py) (`RobotMaster`), [`../../_shared/word_tools.py`](../../_shared/word_tools.py) (`split_word`) |

> 💡 **포트는 반드시 분리** — 세 시뮬레이터는 6000/1502/1503으로 **서로 다른 포트** 를 씁니다. 같은 포트로 두 개를 띄우면 뒤에 뜬 쪽이 `Address already in use` 로 죽습니다. 터미널은 총 **4개** (시뮬레이터 3 + 컨트롤러 1)입니다.

## 핵심 개념

세 장치의 "약속(레지스터/패킷)" 입니다. 이미 03·06·07편에서 검증한 값 그대로이며, 이번 편은 이를 **하나의 흐름** 으로 엮습니다.

**① 비전 (TCP, 03편)** — 컨트롤러가 `{TRIG}` 송신, 비전이 좌표 응답.

| 송신 | 응답 (X mm, Y mm, 회전각 deg) |
|------|-------------------------------|
| `{TRIG}`  | `{123.45,67.89,30.0}` |
| `{TRIG2}` | `{-45.10,210.00,-15.0}` (음수 좌표) |

**② 로봇 (Modbus, 06편)** — 명령 사이클.

| 레지스터 | 의미 |
|----------|------|
| HR **201** | 명령번호 (1=LIN, 4=GO HOME) |
| HR **202** | 모션타입 (1=Cartesian) |
| HR **203~214** | 6축 L/H 쌍 — 직교 X,Y,Z,A,B,C (각 ×1000, `split_word`) |
| HR **215~218** | 속도% / 가속% / Tool / Base |
| HR **200** | 실행 트리거 (1 쓰고, 완료 후 0 리셋) |
| IR **200** | 명령상태 (1=Success) |
| IR **400~411** | 직교 현재위치 L/H |
| IR **524** | 동작상태 (1=Idle, 2=Running) |

**③ 그리퍼 (Modbus, 07편)** — 열기/닫기 사이클.

| 레지스터 | 의미 |
|----------|------|
| HR **1600** | 방향 (0=닫기, 1=열기) |
| HR **1601** | 이동 행정 [0.01mm] |
| HR **1606** | 실행 (1 쓰면 동작 → 완료 후 **0 자동 복귀**) |
| IR **769** | 상태 (2=Pos 도달) |
| IR **770** | 현재 위치 [0.01mm] |

> **좌표 인코딩 한 줄** — `from word_tools import split_word` 후 `split_word(round(123.45*1000))` → 두 word. `RobotMaster.write_holding()` 이 음수 word를 `& 0xFFFF` 로 자동 인코딩하므로 **음수 좌표도 그대로 전달** 하면 됩니다.

### ⚠️ 통합의 두 함정 — 상태 잔상(latch)

세 장치를 직렬로 이으면, **직전 동작의 완료 신호가 레지스터에 그대로 남아(latch)** 다음 동작이 시작하기도 전에 폴링이 통과해 버리는 문제가 생깁니다. 이번 편은 검증된 두 가지 방어를 씁니다.

1. **로봇 완료는 2단계 폴링.** `IR524==1(Idle)` 하나만 보면 직전 명령의 Idle 가 남아 즉시 통과합니다. 그래서 **먼저 `IR524==2(Running)` 시작을 기다린 뒤**, 그다음 `IR524==1(Idle) & IR200==1(Success)` 완료를 기다립니다. 또한 `HR200=0` 리셋 직후 곧바로 다음 트리거를 쓰면 로봇이 리셋을 보지 못해 명령이 잠기므로, 리셋 뒤 폴링 한두 주기를 비워 둡니다.
2. **그리퍼 완료는 `IR769==2` 그리고 `HR1606==0` 을 함께 확인.** 직전 닫기의 `IR769==2(Pos)` 가 남아 있어, 열기 트리거 직후 폴링이 즉시 통과(아직 안 움직였는데 완료로 오판)합니다. 그리퍼가 완료 시 스스로 0으로 되돌리는 `HR1606` 을 동반 확인해 "이번 동작" 의 완료를 분명히 합니다.

## 예제로 보기

전체 코드는 [`src/cell_controller/main.py`](src/cell_controller/main.py) 입니다. 함수가 `get_vision / robot_move / gripper_act / go_home` 으로 분리돼 있어 각 단계를 독립적으로 읽고 디버깅할 수 있습니다.

비전 좌표 받기 — 표준 `socket` 으로 `{TRIG}` 를 보내고 `{X,Y,R}` 를 파싱합니다.

```python
def get_vision(host, port, trig="TRIG"):
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall(("{" + trig + "}").encode("ascii"))   # {TRIG} 송신
        raw = s.recv(1024).decode("ascii")               # {123.45,67.89,30.0}
    parts = [p.strip() for p in raw.replace("{", "").replace("}", "").strip().split(",")]
    return float(parts[0]), float(parts[1]), float(parts[2])
```

로봇 LIN 이동 — 6축을 `split_word` 로 인코딩해 한 번에 쓰고, **2단계로 완료를 폴링** 합니다.

```python
def robot_move(m, x, y, z, a=0.0, b=0.0, c=0.0, cmd=1, mtype=1):
    axis = []
    for v in (x, y, z, a, b, c):
        low, high = split_word(round(v * 1000))   # ×1000 정수화 후 32bit 분할
        axis += [low, high]                        # [L, H] 순서, 음수도 그대로
    m.write_holding(201, [cmd, mtype] + axis + [50, 100, 1, 0])  # HR201~218
    m.write_holding(200, 1)                        # 실행 트리거
    _wait_robot(m)                                 # ↓ 2단계 폴링
    m.write_holding(200, 0); time.sleep(POLL * 2)  # 리셋 + 인지 대기

def _wait_robot(m):
    while m.read_input(524, 1)[0] != 2:            # ① Running(2) 시작을 먼저 기다림
        time.sleep(POLL)                           #    (직전 Idle latch 회피)
    while not (m.read_input(524,1)[0]==1 and m.read_input(200,1)[0]==1):  # ② 완료
        time.sleep(POLL)
```

그리퍼 동작 — `IR769==2` **그리고** `HR1606==0` 을 함께 확인합니다.

```python
def gripper_act(m, direction, stroke):   # direction 0=닫기(집기) / 1=열기(놓기)
    m.write_holding(1600, direction); m.write_holding(1601, stroke)
    m.write_holding(1606, 1)             # 실행 트리거
    while not (m.read_input(769,1)[0]==2 and m.read_holding(1606,1)[0]==0):  # 잔상 회피
        time.sleep(POLL)
```

한 사이클의 흐름(`run_cycle`)은 위 함수들을 픽(2단 Z) → 집기 → 상승 → 플레이스 → 놓기 → 원점 복귀로 엮습니다. 로봇·그리퍼 연결은 `with RobotMaster(...) as robot, RobotMaster(...) as gripper:` 로 **한 번 열어 여러 사이클에 재사용** 합니다.

## 실행/검증해 보기

세 시뮬레이터를 각각의 터미널에 띄우고, 네 번째 터미널에서 컨트롤러를 실행합니다. 콘솔 한글 깨짐 방지를 위해 각 터미널에서 `set PYTHONUTF8=1`(PowerShell은 `$env:PYTHONUTF8=1`)을 먼저 실행하세요.

**터미널 1 (비전) · 터미널 2 (로봇) · 터미널 3 (그리퍼)** — 켜둔 채로 둡니다.

```powershell
cd lecture/08_capstone/09_cell
python ../../_shared/tcp_echo_server.py  --mode vision --port 6000        # 터미널 1
python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1     # 터미널 2
python ../../_shared/gripper_sim.py      --port 1503 --host 127.0.0.1     # 터미널 3
```

**터미널 4 (셀 제어기)** — 한 사이클 실행:

```powershell
python src/cell_controller/main.py
```

실제 콘솔 출력 (검증됨):

```text
============================================================
 비전·로봇·그리퍼 자동화 셀 컨트롤러 시작
  비전  127.0.0.1:6000  (TCP)
  로봇  127.0.0.1:1502  (Modbus)
  그리퍼 127.0.0.1:1503  (Modbus)
============================================================

----- 사이클 1/1  (trigger TRIG) -----
[1] 비전 시스템(127.0.0.1:6000)에 부품 위치 요청 …
  [VISION] 송신 {TRIG}
  [VISION] 수신 {123.45,67.89,30.0}
    → 부품 좌표  X=123.45 mm  Y=67.89 mm  회전각 R=30.0 deg
[2] 픽 동작 (접근 → 하강 → 집기) …
[로봇] LIN 이동 → 픽 접근 (123.45,67.89,Z=50.0)
  [ROBOT] 이동 완료 (IR200=1 Success, IR524=1 Idle)
[로봇] LIN 이동 → 픽 하강 (123.45,67.89,Z=5.0)
  [ROBOT] 이동 완료 (IR200=1 Success, IR524=1 Idle)
[그리퍼] 닫기(집기) → 행정 40.00 mm
  [GRIPPER] 완료 (IR769=2 Pos, IR770=0=0.00mm, HR1606=0 자동복귀)
[로봇] LIN 이동 → 픽 상승 (123.45,67.89,Z=50.0)
  [ROBOT] 이동 완료 (IR200=1 Success, IR524=1 Idle)
[3] 플레이스 동작 (이동 → 놓기) …
[로봇] LIN 이동 → 플레이스 이동 (200.0,0.0,Z=50.0)
  [ROBOT] 이동 완료 (IR200=1 Success, IR524=1 Idle)
[그리퍼] 열기(놓기) → 행정 60.00 mm
  [GRIPPER] 완료 (IR769=2 Pos, IR770=6000=60.00mm, HR1606=0 자동복귀)
[4] 마무리 …
[로봇] GO HOME (원점 복귀) …
  [ROBOT] 원점 복귀 완료 (IR400~411 = 0)
=== 사이클 완료 (cycle time 4.21s) ===

============================================================
 전체 1 사이클 완료. 평균 cycle time 4.21s (min 4.21s / max 4.21s)
============================================================
```

각 시뮬레이터 터미널에도 로그가 찍힙니다(로봇 `▶ 명령 시작: 1 (LIN)` / `✔ 명령 완료`, 그리퍼 `▶ 그리퍼 닫기` / `✔ 동작 완료`).

✅ **체크포인트**: 비전 수신 → 픽(2단 Z) → 집기 → 상승 → 플레이스 → 놓기 → 원점 복귀가 **한 번도 멈추지 않고** 완주하고 `사이클 완료` 가 뜨면, 03·06·07편을 하나로 통합한 자동화 셀을 완성한 것입니다. (cycle time 숫자는 환경에 따라 다릅니다.)

> 💡 **음수 좌표 / 반복 실행** — `--trig TRIG2` 로 음수 좌표 `{-45.10,210.00,-15.0}` 사이클을, `--cycles 2` 로 `TRIG`→`TRIG2` 두 부품을 연속 처리합니다(직접 해 보기). 마지막 줄에 **평균/최소/최대 cycle time** 이 출력됩니다.

## 자주 하는 실수

### Q. 두 번째 이동부터 로봇이 **즉시 "완료"** 로 표시돼요(실제로는 안 움직임).
A. `IR524==1(Idle)` 하나만 보면 직전 명령의 Idle 가 **latch** 로 남아 새 명령 시작 전에 통과합니다. **먼저 `IR524==2(Running)` 시작을 기다린 뒤** `IR524==1 & IR200==1` 완료를 보세요(2단계 폴링).

### Q. 두 번째 이동부터 로봇이 **아예 안 움직이고 타임아웃** 나요.
A. `HR200=0` 리셋 직후 곧바로 다음 `HR200=1` 을 쓰면, 로봇 로직이 `0` 을 한 번도 못 봐 ack 가 풀리지 않고 명령이 잠깁니다(매뉴얼 5.3.3.5 절차 ⑤). 리셋 후 폴링 한두 주기를 비워 두세요(`_reset_robot_trigger`).

### Q. 그리퍼 열기가 **즉시 완료로 표시** 돼요(안 움직임).
A. 직전 닫기의 `IR769==2(Pos)` 잔상으로 폴링이 조기 통과한 것입니다. 완료 조건에 `HR1606==0` 을 **함께** 확인하세요. 그리퍼가 완료 시 자동으로 0으로 되돌립니다.

### Q. 시뮬레이터가 `Address already in use` 로 안 떠요.
A. 세 시뮬레이터가 같은 포트를 쓰거나, 이전 프로세스가 포트를 점유 중입니다. 6000/1502/1503으로 **포트를 분리** 하고, 기존 터미널을 Ctrl+C 후 재실행하세요. 다른 포트로 띄웠다면 컨트롤러에 `--vision-port/--robot-port/--gripper-port` 로 전달합니다.

## 🚀 확장 과제
- **음수 좌표 처리** — `--trig TRIG2` 사이클을 완주하고, 로봇 `IR400~411` 을 디코딩해 X가 `-45.10` 으로 정확히 들어갔는지 확인(음수 word `& 0xFFFF` 왕복 이해).
- **여러 부품 반복 처리** — `--cycles N` 으로 `TRIG`/`TRIG2` 를 번갈아 N개 처리하고, **연결을 매 사이클 새로 열지 않고 재사용** 하며 평균 사이클 타임을 출력.
- **모니터링 결합([08편](../../07_debug/08_monitoring/README.md))** — `tcp.port==1502 || tcp.port==1503 || tcp.port==6000` 필터로 세 장치 트래픽을 동시에 관찰. LIN 이동의 `10h`(Write Multiple)와 그리퍼 `10h`/`04h` 패턴을 식별.
- **에러 복구 시나리오** — 그리퍼가 부품을 놓쳤다고 가정(`IR770` 이 목표와 다름)하고, 실패 시 재시도 또는 안전 정지(GO HOME 후 경보) 로직을 추가.
- **🤖 실장비 이식** — 컨트롤러를 HRSS로 옮기면 비전은 `COPEN/CWRITE/CREAD`([03편](../../03_network/03_tcpip/README.md)), 그리퍼는 `MBC_RTU_OPEN`+`MBC_WRITE/READ`([07편](../../06_client/07_modbus_client/README.md))가 됩니다. 시뮬레이터에서 익힌 **순서와 상태 폴링** 이 그대로 옮겨집니다.

## 정리 & 강의 마무리
- **자동화 셀** = 비전(TCP/IP) + 로봇(Modbus 명령 사이클) + 그리퍼(Modbus 사이클) + 원점 복귀를 **한 컨트롤러로 오케스트레이션**. 03·06·07·08편이 한 시나리오에서 만납니다.
- 컨트롤러는 비전에 **TCP Client**, 로봇·그리퍼에 **Modbus Master**. 역할은 "누가 먼저 말을 거는가" 로 가립니다.
- 비전 실수 좌표 → `split_word(round(v*1000))` → 직교 LIN. **음수 좌표도 `& 0xFFFF` 자동 인코딩** 으로 그대로 왕복.
- 단계 연결의 핵심은 **상태 폴링으로 직렬화**: 로봇은 `IR524=2→1 & IR200=1` 2단계 + `HR200=0` 리셋 인지, 그리퍼는 `IR769=2 & HR1606=0`. **상태 잔상(latch)** 을 피하는 것이 통합의 함정이자 요점입니다.

🎓 **강의를 마치며** — [01 환경준비](../../01_intro/01_setup/README.md)에서 시작해 I/O · TCP/IP · RS-232 · Modbus 기초 · 로봇=Server · 로봇=Client · 모니터링을 거쳐, 이제 그 모두를 묶은 **자동화 셀** 까지 완성했습니다. 실장비 없이 PC 한 대로 산업용 로봇 통신의 전 범위를 **손으로 실습** 했습니다. 다음 단계는 이 시뮬레이터들을 실제 HIWIN 로봇·XEG 그리퍼·산업용 카메라로 **하나씩 치환** 하는 것뿐입니다 — 명령의 **순서와 상태 확인 논리** 는 그대로입니다.

➡️ **돌아가기: [트랙 인덱스](../../README.md)**

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다. (세 시뮬레이터를 모두 띄운 상태에서 실행합니다.)

## 다음 단원
🎉 **축하합니다 — 9편 완주!** 이 편이 트랙의 마지막입니다. 전체를 한 장으로 복습하려면 부록 [치트시트](../../appendix/cheatsheet.md)를, 32bit/IEEE754 변환은 [변환 부록](../../appendix/word-conversion.md)을, 확인 문제 풀이는 [해답 부록](../../appendix/solutions.md)을 참고하세요. 처음으로 돌아가려면 [트랙 인덱스](../../README.md)로.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication User Manual* (C25UE801-2211) — 전 범위
  - **Ch.3 Ethernet Communication** — `COPEN/CWRITE/CREAD`, `{data}` 패킷 규약 (비전 송수신)
  - **Ch.5.3 MODBUS Server** — 로봇=Slave, 명령 실행 절차 5.3.3.5 (HR201→HR200=1→IR524/IR200 폴링→HR200=0)
  - **Ch.5.4 MODBUS Client** — 로봇=Master, 5.4.5.1 XEG 그리퍼 제어 (1600/1601/1606, IR769/770)
  - **Ch.5.5 Monitoring** — 셀 트래픽 캡처·해독
  - **Appendix II** — 32bit Low/High word 분할 (좌표 인코딩)
- 통합 코드: [`src/cell_controller/main.py`](src/cell_controller/main.py) · 시뮬레이터: [`../../_shared/`](../../_shared/)
