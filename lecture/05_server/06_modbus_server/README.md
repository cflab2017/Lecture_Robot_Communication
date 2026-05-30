# 06. MODBUS SERVER (로봇 = 슬레이브)

앞선 [05. MODBUS 기초](../../04_modbus/05_modbus_basics/README.md)에서는 4종 레지스터(Discrete Input / Coil / Input Register / Holding Register)를 **개별적으로** 읽고 썼습니다. 이번 편은 그 레지스터들을 **엮어서 로봇을 제어**합니다. 로봇을 **Slave(Server)** 로 두고, 상위 PLC·PC를 **Master(Client)** 로 삼아 "**명령 번호 입력 → 파라미터 입력 → 트리거 → 동작 → 응답 확인 → 리셋**"이라는 **명령 사이클**을 돌립니다. 현장에서 PLC가 HIWIN 로봇을 움직이는 실제 방식이며, 본 트랙의 핵심입니다. 실제 로봇 없이 [`_shared/robot_server_sim.py`](../../_shared/robot_server_sim.py)(로봇 = 슬레이브)와 [`_shared/modbus_master.py`](../../_shared/modbus_master.py)의 `RobotMaster`(PLC = 마스터)로 **PC 한 대**에서 전 과정을 재현합니다.

## 학습 목표
- **로봇 = Slave Server, PLC = Master Client** 구조에서 누가 명령을 보내고 누가 동작하는지 설명한다.
- 로봇의 **SO/SI/DI/DO 및 명령·상태 레지스터**가 4종 레지스터 영역에 어떻게 매핑되는지 표로 정리한다.
- 매뉴얼 5.3.3.5의 **명령 실행 5단계**(`HR201 → HR202~ → HR200=1 → IR200 확인 → HR200=0`)를 직접 수행한다.
- **PTP / LIN / GO HOME** 명령을 마스터에서 전송하고, **32bit 좌표·각도를 Low/High word로 분할**해 넣는다.
- 단일 명령 **17종 카테고리**(모션·Tool/Base·PR/Home·T_STOP)의 명령 번호를 분류한다.

## 대상 환경
- 도구: Python 3.10+ / pymodbus 3.6.9 / `_shared/modbus_master.py`·`word_tools.py`
- 플랫폼: Windows PC (시뮬레이션) — 실제 로봇/PLC 불필요. 실장비 측은 HRSS·Caterpillar
- 검증: 터미널 A에 로봇 슬레이브(`robot_server_sim.py`)를 띄우고, 터미널 B에서 `python src/server_motion/main.py`

## 핵심 개념

### 1) 로봇이 "슬레이브"가 된다는 것
```
   ┌────────────────┐   Demand (명령 쓰기 / 상태 읽기) ─►   ┌──────────────────┐
   │  Master/Client │                                       │  Slave / Server  │
   │  상위 PLC · PC  │   ◄── Response (레지스터 값 응답)      │   HIWIN 로봇      │
   └────────────────┘                                       └──────────────────┘
```
- **Master(상위 PLC/PC)** 가 로봇의 Holding Register에 **명령 번호·파라미터·트리거**를 써넣습니다.
- **Slave(로봇)** 는 그 값을 보고 **실제로 움직이며**, 진행 상태·현재 위치를 Input Register/Discrete Input에 채워 응답합니다.
- 로봇은 명령을 **받기만** 하고 능동적으로 보내지 않습니다 — "제어받는 입장". 로봇이 그리퍼·센서를 **제어하는** 반대 입장은 [07. MODBUS CLIENT](../../06_client/07_modbus_client/README.md)에서 다룹니다.

### 2) 로봇 신호·상태가 4종 레지스터에 매핑된다 (매뉴얼 Table 11)
| 레지스터 영역 | 권한 | 로봇 쪽 의미 |
|----------------|:---:|--------------|
| **Discrete Input** | R | **SO**(Fieldbus 출력: Run/Held/Fault/Ready…), **DI**(디지털 입력) 읽기 |
| **Coil** | R/W | **SI**(Fieldbus 입력: Start/Hold/Stop/Enable…), **DO**(디지털 출력) 읽기/쓰기 |
| **Input Register** | R | **현재 속도·동작 상태·현재 명령·관절/직교 위치** 읽기 |
| **Holding Register** | R/W | **속도 설정·명령 번호·명령 파라미터·Timer/Counter/PR** 읽기/쓰기 |

> 마스터는 **R/W 영역(Coil·Holding Register)** 으로 로봇에 **명령**하고, **R 영역(Discrete Input·Input Register)** 으로 로봇 **상태를 감시**합니다. 05편의 "읽기 전용 vs 읽기/쓰기" 권한 차이가 곧 "감시 vs 명령"의 구분이 됩니다.

### 3) 연결 설정 4종 요약 (매뉴얼 5.3.2)
실장비에서는 HRSS/Caterpillar UI로 서버를 활성화합니다. 경로는 **Fieldbus → Setting** 이며, 4가지 조합 모두 **Channel 선택 → Connection Type 선택 → 식별자 설정** 순서입니다.

| 설정 종류 | 소프트웨어 | 핵심 설정 항목 |
|-----------|-----------|----------------|
| **HRSS Modbus RTU Server** | HRSS (Expert) | Channel1/2 · `Modbus RTU Server` · **Slave ID** · COMPORT(parity/stop/baud/data) |
| **HRSS Modbus TCP Server** | HRSS (Expert) | Channel1/2 · `Modbus TCP Server` · **Local IP** · **Local Port** |
| **Caterpillar Modbus RTU Server** | Caterpillar (SCARA LU) | Channel1/2 · `Modbus RTU Server` · **Slave ID** · COMPORT |
| **Caterpillar Modbus TCP Server** | Caterpillar (SCARA LU) | Channel1/2 · `Modbus TCP Server` · **Local Port** |

> 본 실습은 PC 1대이므로 **Modbus TCP**(`127.0.0.1`)를 쓰며, 데이터 모델은 RTU와 동일합니다.

### 4) 레지스터 맵 (매뉴얼 5.3.3 ↔ 시뮬레이터 `zero_mode`, 0-base)
| 영역 | 주소 | 의미 |
|------|------|------|
| **Discrete Input** (R) | `0~` | SO1~ (SO1=Run, SO2=Held, SO3=Fault, **SO4=Ready**), `300~` DI |
| **Coil** (R/W) | `0~` | SI1~ (**SI1=Start**, SI2=Hold, SI3=Stop, SI4=Enable), `300~` DO |
| **Input Register** (R) | `200` | **명령 상태** (0=진행, 1=Success, 2=Fail) |
| | `201` | 현재 실행 명령 번호 |
| | `300~311` | **관절** A1~A6 (각 축 Low/High word 쌍, 0.001°) |
| | `400~411` | **직교** X·Y·Z·A·B·C (각 축 L/H 쌍, 0.001mm·0.001°) |
| | `524` | **동작 상태** (1=Idle, 2=Running) |
| **Holding Register** (R/W) | `200` | **실행 트리거** (0=Ready, 1=실행) |
| | `201` | **명령 번호** (0=PTP, 1=LIN, 3=JOG, 4=GO HOME …) |
| | `202` | 모션 타입 (0=Joint, 1=Cartesian) |
| | `203~214` | 6축 값 L/H 쌍 (A1L,A1H,…,A6H) — 12워드 |
| | `215/216` | 속도% / 가속% |
| | `217/218` | Tool 번호 / Base 번호 |

### 5) 명령 실행 절차 5단계 (매뉴얼 5.3.3.5)
```
 ① HR[201] ← 명령 번호       (예: 0 = PTP)
 ② HR[202~] ← 파라미터        (모션 타입, 6축 좌표, 속도, Tool/Base …)
 ③ HR[200] ← 1               (실행 트리거)
 ④ 로봇 동작 → IR[524] 2(Run)→1(Idle), IR[200] = 1(Success)
 ⑤ HR[200] ← 0               (마스터가 리셋 → 다음 명령 준비)
```
> **핵심 규칙**: ⑤에서 `HR[200]`을 0으로 리셋하지 않으면 **다음 명령이 실행되지 않습니다**.

### 6) 32bit 값의 Low/High word 분할
관절 각도·좌표는 **0.001 단위 정수**입니다. `90.000° → 90000`. 그런데 16bit word는 **-32768~32767** 까지만 담으므로 한 word에 못 들어갑니다. 그래서 **Low/High word 두 개**로 나눠 32bit로 표현합니다.

```python
from word_tools import split_word
split_word(90000)      # → (24464, 1)   Low=90000%65536, High=90000//65536
# 복원: 1×65536 + 24464 = 90000 → ×0.001 = 90.000°
```
> 음수 좌표(예: `-300mm`)는 High word가 음수(`-5`)가 됩니다. 분할/복원 원리와 부호 처리는 [부록 B(32bit·IEEE754 변환)](../../appendix/word-conversion.md)에서 자세히 다룹니다. `RobotMaster.write_holding()` 은 음수 word를 **자동으로 unsigned(`& 0xFFFF`) 인코딩**하므로 마스터 코드에서 별도 처리가 필요 없습니다.

### 7) 단일 명령 17종 카테고리 (매뉴얼 Table 16)
마스터가 `HR[201]`에 넣는 **명령 번호**의 전체 목록입니다.

| 카테고리 | 명령 번호 · 이름 |
|----------|------------------|
| **모션** | 000 PTP · 001 LIN · 002 CIRC · 003 JOG · 004 GO HOME · 006 Motion Stop |
| **T_STOP** | 005 T_STOP (Timer 정지) |
| **Set Tool/Base** | 101 Set Tool · 102 Set Base · 103 Set Current Tool · 104 Set Current Base |
| **Get Tool/Base** | 201 Get Tool · 202 Get Base · 203 Get Current Tool · 204 Get Current Base |
| **PR / Home** | 100 Set PR · 105 Set Home · 200 Get PR · 205 Get Home |

> **규칙**: `000~006` = 모션 계열, `100·105` = Set PR/Home, `101~104` = Tool/Base 설정, `200~205` = 같은 항목의 **Get(조회)**. Set 계열은 Holding Register로 값을 보내고, Get 계열은 Input Register로 값이 돌아옵니다.

## 예제로 보기

### `src/server_motion/main.py` : PTP 명령 사이클
마스터(PLC) 역할로 로봇 슬레이브에 **A1 관절을 90°로 PTP 이동**시킵니다. 명령 실행 5단계를 그대로 콘솔에 출력합니다. (전체 코드는 파일 참조)

```python
from modbus_master import RobotMaster
from word_tools import split_word

A1_low, A1_high = split_word(90000)        # (24464, 1) = 90.000°

with RobotMaster(args.host, args.port) as m:
    # ①② HR[201..218] 한 번에: 201=명령번호(0=PTP), 202=모션타입(0=Joint),
    #     203~214=6축 L/H, 215~218=속도/가속/Tool/Base
    params = [0, 0, A1_low, A1_high, 0,0,0,0,0,0,0,0,0,0, 50, 100, 1, 2]
    m.write_holding(201, params)
    m.write_holding(200, 1)                 # ③ 실행 트리거

    # ④ 직전 명령의 Success/Idle 가 남아 있을 수 있으므로
    #    먼저 시작(Running=2)을 기다린 뒤 완료(Idle+Success)를 기다린다.
    while m.read_input(524, 1)[0] != 2:
        time.sleep(0.02)
    while not (m.read_input(524, 1)[0] == 1 and m.read_input(200, 1)[0] == 1):
        time.sleep(0.05)

    print("현재 관절 IR[300:302] =", m.read_input(300, 2))   # [24464, 1]
    m.write_holding(200, 0)                 # ⑤ 트리거 리셋
```

## 실행/검증해 보기

### 터미널 A — 로봇 슬레이브(서버) 띄우기
이 창은 켜둔 채 둡니다.
```powershell
cd lecture/_shared
set PYTHONUTF8=1
python robot_server_sim.py --port 1502 --host 127.0.0.1
```
```text
============================================================
 로봇 Modbus SERVER 시뮬레이터  127.0.0.1:1502  (Slave ID 1)
 마스터(modbus_master.py / QModMaster)로 접속해 명령 사이클을 실습하세요.
============================================================
로봇 로직 스레드 시작.
```

### 터미널 B — 마스터(PTP 사이클) 실행
```powershell
cd lecture/05_server/06_modbus_server
set PYTHONUTF8=1
python src/server_motion/main.py --port 1502
```
예상 출력:
```text
=== PTP 명령 사이클 (A1=90° 각도 이동) ===
[①] HR[201]=0(PTP), HR[202]=0(Joint), HR[203:205]=[24464, 1]  (split_word(90000))
[②] HR[215:219]=[50, 100, 1, 2]  속도50% / 가속100% / Tool1 / Base2
[③] HR[200]<-1  실행 트리거
[④] 동작 완료 대기... IR[524]=1(Idle), IR[200]=1(Success)
    현재 관절 IR[300:302] = [24464, 1]  ->  90.000°
[⑤] HR[200]<-0  트리거 리셋 (다음 명령 준비)
PTP 사이클 완료 ✅
```

터미널 A(서버)에는 동작 로그가 함께 찍힙니다.
```text
  ▶ 명령 시작: 0 (PTP)
     관절 이동 완료 A1~A6 = [90.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  ✔ 명령 완료: IR[200]=1(Success). 마스터는 HR[200]<-0 으로 리셋하세요.
```

✅ **체크포인트**: `IR[300,301] = [24464, 1]` → `1×65536 + 24464 = 90000` → **90.000°**, 명령 상태 `IR[200]=1(Success)`. 명령 실행 절차 ①~⑤를 한 사이클 완주했습니다.

## 자주 하는 실수

### Q. 트리거를 1로 썼는데 로봇이 안 움직여요.
A. 직전 명령의 `HR[200]`을 0으로 **리셋하지 않은** 경우입니다. 절차 ⑤(`m.write_holding(200, 0)`)를 빠뜨리면 슬레이브가 `ack_wait` 상태에서 다음 트리거를 무시합니다 — 매뉴얼 5.3.3.5의 핵심 규칙입니다.

### Q. `IR[200]`이 계속 0이에요.
A. 동작이 아직 진행 중(`IR[524]=2`)이거나 트리거가 안 들어간 경우입니다. `IR[524]`가 1(Idle)이 될 때까지 폴링한 뒤 `IR[200]`을 확인하세요. 본 예제처럼 두 조건을 함께 검사하는 것이 안전합니다.

### Q. 음수 좌표(`X=-300mm`)를 쓸 때 `struct.error: 'H' format requires 0 <= number <= 65535`가 나요.
A. `split_word(-300000) = (27680, -5)` 로 High word가 음수입니다. Modbus 레지스터 쓰기는 unsigned 16bit만 받으므로 음수를 그대로 쓰면 오류가 납니다. `RobotMaster.write_holding()` 은 내부에서 `값 & 0xFFFF` 로 자동 인코딩(`-5 → 65531`)하므로, **`RobotMaster`를 쓰면 추가 처리가 필요 없습니다**. 직접 `write_registers`를 호출할 때만 수동 변환이 필요합니다.

### Q. 좌표·각도가 엉뚱한 값으로 들어가요.
A. L/H 워드 **순서**(`[Low, High]`)나 모션 타입(`HR202`: Joint=0 / Cartesian=1) 착오입니다. `split_word()` 결과를 그 순서대로 넣었는지 확인하세요.

## 정리
- 로봇 = **Slave Server**, 상위 PLC/PC = **Master Client**. 마스터는 **R/W 영역**으로 명령하고 **R 영역**으로 감시한다.
- **명령 사이클**: `HR201=명령번호 → HR202~=파라미터 → HR200=1 → IR200/IR524 확인 → HR200=0 리셋`. 리셋은 필수다.
- 16bit를 넘는 좌표·각도는 `split_word()` 로 **Low/High word 분할**(90°→`(24464,1)`, -300mm→`(27680,-5)`)하고, 음수 word는 `RobotMaster`가 자동 인코딩한다.
- 단일 명령 17종은 모션(000~006)·T_STOP(005)·Tool/Base(101~104, 201~204)·PR/Home(100·105·200·205)으로 분류된다.

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[07. MODBUS CLIENT (로봇 = 마스터)](../../06_client/07_modbus_client/README.md) — 이번 편은 로봇이 **제어받는** 입장이었습니다. 다음 편은 로봇이 **마스터**가 되어 그리퍼·PLC를 제어하는 반대 입장을 다루며, IEEE754 부동소수점 변환까지 확장합니다.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication User Manual* (C25UE801-2211)
  - **Ch.5.3.1 Function Application** (p.41, Table 11 매핑 개요)
  - **Ch.5.3.2 Interface Setting** (p.42~45, RTU·TCP Server 연결 4종)
  - **Ch.5.3.3.1~5.3.3.4 Data Setting Table** (p.46~54, Table 12~15)
  - **Ch.5.3.3.5 Sending Commands** (p.55, 명령 실행 절차)
  - **Ch.5.3.3.6 Command Parameter Table** (p.55~80, Table 16 명령 17종)
- 32bit 분할 변환: [부록 B](../../appendix/word-conversion.md)
