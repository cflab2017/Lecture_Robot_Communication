# 07. MODBUS CLIENT (로봇 = 마스터)

앞선 [06. MODBUS SERVER](../../05_server/06_modbus_server/README.md)에서 로봇은 **제어받는** 입장(Slave Server)이었습니다. 이번 편은 입장을 뒤집습니다. 로봇이 **Master Client**가 되어 전동 그리퍼·다른 로봇·PLC를 **능동적으로 제어**합니다. HIWIN 로봇 언어의 `MBC_*` 명령으로 한 로봇이 **최대 4개의 Server와 동시에** 연결해 4종 데이터(Discrete Input / Coil / Input Register / Holding Register)를 읽고 씁니다. 실제 그리퍼 없이 [`_shared/gripper_sim.py`](../../_shared/gripper_sim.py)(그리퍼 = Server)와 [`_shared/modbus_master.py`](../../_shared/modbus_master.py)의 `RobotMaster`(로봇 = Client)로 **PC 한 대**에서 전 과정을 재현합니다.

## 학습 목표
- **로봇 = Master Client** 구조에서 로봇이 그리퍼·PLC·다른 로봇을 어떻게 능동 제어하는지 설명한다.
- 한 로봇이 **최대 4개 Server와 동시 연결**하는 구조와 **연결 번호(1~4)**의 의미를 안다.
- `MBC_RTU_OPEN`/`MBC_TCP_OPEN` 등 **연결 명령**과 `MBC_READ_*`/`MBC_WRITE_*` **데이터 명령**의 인자를 구분해 쓴다.
- **Bit 명령**(Discrete Input / Coil)과 **Word 명령**(Input / Holding Register, `'W'`/`'D'` 타입)의 차이를 설명한다.
- `SWAP_WORD`/`IEEE754_ENCODE`/`IEEE754_DECODE`가 **왜 필요한지**(Modbus는 실수 직접 전송 불가, 장비별 byte order 차이) 알고 직접 변환한다.

## 대상 환경
- 도구: Python 3.10+ / pymodbus 3.6.9 / `_shared/modbus_master.py`·`word_tools.py`
- 플랫폼: Windows PC (시뮬레이션) — 실제 로봇/PLC/그리퍼 불필요. 실장비 측은 HRSS·Caterpillar
- 검증: 터미널 A에 그리퍼 서버(`gripper_sim.py`)를 띄우고, 터미널 B에서 `python src/client_gripper/main.py`

## 핵심 개념

### 1) 로봇이 "마스터"가 된다는 것
```
   ┌──────────────────┐  Demand (읽기/쓰기 요청) ─►   ┌──────────────────┐
   │  Master / Client │                                │  Slave / Server  │
   │   HIWIN 로봇      │  ◄── Response (값 / 응답)      │ 그리퍼·PLC·로봇B │
   └──────────────────┘                                └──────────────────┘
         (능동)                                              (수동)
```
- **로봇(Master/Client)**이 먼저 요청을 보냅니다. 그리퍼의 Holding Register에 "열어라"를 쓰고, PLC의 Input Register에서 센서 값을 읽어옵니다.
- **상대 장비(Slave/Server)**는 요청받은 값을 응답할 뿐, 먼저 말을 걸지 않습니다.
- 06편과 정반대입니다. **06편: 로봇=Server(수동) / 07편: 로봇=Client(능동)**. 같은 로봇이라도 통신 역할은 설정에 따라 달라집니다.

### 2) 한 로봇 = 최대 4개 Server 동시 연결
로봇 하나가 그리퍼(연결 1), PLC(연결 2), 비전(연결 3), 다른 로봇(연결 4)을 **동시에** 제어할 수 있습니다. 각 연결은 **연결 번호 1~4**로 구분하며, 모든 `MBC_*` 데이터 명령의 첫 인자가 바로 이 번호입니다.
```
   로봇 ──(연결 1)── 전동 그리퍼   (RTU)
        ──(연결 2)── PLC          (TCP)
        ──(연결 3)── 비전 시스템   (TCP)
        ──(연결 4)── 다른 로봇 B   (TCP)
```

### 3) MBC_* 명령 한눈에 (매뉴얼 Table 54)
| 분류 | 명령 | 용도 | 주요 인자 |
|------|------|------|-----------|
| **연결(RTU)** | `MBC_RTU_OPEN` | RTU Client 연결 시작 | (연결수 1~4, SlaveID배열, Baud, Parity `'N'/'O'/'E'`, DataBit 5~8, StopBit 1/2, COM) |
| | `MBC_RTU_CLOSE` | RTU 연결 종료 | (없음) |
| **연결(TCP)** | `MBC_TCP_OPEN` | TCP Client 연결 시작 | (연결번호 1~4, `"IP"`, Port) |
| | `MBC_TCP_CLOSE` | TCP 연결 종료 | (연결번호 1~4) |
| **Bit 읽기** | `MBC_READ_DINPUT` | Discrete Input 읽기 | (연결번호, 시작주소, 데이터변수, 길이 1~48) |
| | `MBC_READ_COIL` | Coil 읽기 | (연결번호, 시작주소, 데이터변수, 길이 1~48) |
| **Bit 쓰기** | `MBC_WRITE_COIL` | Coil 쓰기 | (연결번호, 시작주소, 데이터변수, 길이 1~48) |
| **Word 읽기** | `MBC_READ_INPUT` | Input Register 읽기 | (연결번호, 시작주소, 데이터변수, 타입 `'W'/'D'`, 길이) |
| | `MBC_READ_HOLDING` | Holding Register 읽기 | (연결번호, 시작주소, 데이터변수, 타입 `'W'/'D'`, 길이) |
| **Word 쓰기** | `MBC_WRITE_HOLDING` | Holding Register 쓰기 | (연결번호, 시작주소, 데이터변수, 타입 `'W'/'D'`, 길이) |

> **시작 주소는 0-base**(HRSS/Caterpillar 화면에서는 1부터). **연결 명령을 먼저** 호출하지 않으면 데이터 명령은 동작하지 않습니다.

**Bit 명령 vs Word 명령** — Word 명령에만 있는 **데이터 타입 인자**가 핵심입니다.

| 구분 | 대상 영역 | 데이터 단위 | 길이 범위 |
|------|-----------|-------------|-----------|
| **Bit** | Discrete Input(R), Coil(R/W) | 0 또는 1 | 1~48 |
| **Word** | Input Register(R), Holding Register(R/W) | 16/32bit 정수 | `'W'` 읽기 1~125·쓰기 1~123 / `'D'` 읽기 1~62·쓰기 1~61 |

- **`'W'` (Word)** — 16bit 레지스터 1개를 그대로. 모델 번호, 속도 % 같은 작은 값.
- **`'D'` (Double Word)** — 연속한 2개 레지스터를 32bit로 합쳐서. 좌표·각도처럼 16bit를 넘는 값. **저장 순서는 Low word 먼저, High word 나중**.

### 4) HRSS `MBC_*` ↔ `RobotMaster` 대응표
로봇(Client) 역할은 PC에서 `RobotMaster`가 대신합니다. 실장비의 `MBC_*` 한 줄이 곧 아래 메서드 한 줄입니다.

| HRSS 로봇 명령 (실장비) | `RobotMaster` 메서드 (💻 PC) |
|---|---|
| `MBC_TCP_OPEN(1,"127.0.0.1",502)` | `with RobotMaster('127.0.0.1', 1503) as m:` |
| `MBC_TCP_CLOSE(1)` | `with` 블록 종료 시 자동 `close()` |
| `MBC_WRITE_HOLDING(1, addr, var, 'W', n)` | `m.write_holding(addr, [..])` |
| `MBC_READ_INPUT(1, addr, var, 'W', n)` | `m.read_input(addr, n)` |
| `MBC_READ_HOLDING(1, addr, var, 'W', n)` | `m.read_holding(addr, n)` |
| `MBC_WRITE_COIL(1, addr, var, n)` | `m.write_coil(addr, v)` / `m.write_coils(addr, [..])` |
| `MBC_READ_DINPUT(1, addr, var, n)` | `m.read_discrete(addr, n)` |
| `MBC_READ_COIL(1, addr, var, n)` | `m.read_coils(addr, n)` |
| `SWAP_WORD(v)` | `word_tools.swap_word(v)` |
| `IEEE754_ENCODE(f)` | `word_tools.ieee754_encode(f)` |
| `IEEE754_DECODE(i)` | `word_tools.ieee754_decode(i)` |

> 💻 실장비는 그리퍼를 RS485(RTU, 포트 502)로 물리지만, PC에서는 케이블이 없으므로 **TCP + 임의 포트(1503)**로 흉내 냅니다. **데이터 모델·레지스터 주소는 RTU와 동일**합니다.

### 5) 변환 명령은 왜 필요한가
**Modbus 레지스터는 16bit 정수만 실어 나릅니다.** 실수(부동소수점)도, 16bit를 넘는 정수도 직접 못 보냅니다. 게다가 장비마다 **byte order(High/Low word 순서)**가 다릅니다. 그래서:

| 명령 | 역할 |
|------|------|
| `SWAP_WORD` | 32bit 값의 상·하위 word 자리를 교환해 상대 장비 byte order 보정 |
| `IEEE754_ENCODE` | 실수(`10.5`)를 보낼 수 없으니 **실수 → 32bit 정수**(IEEE754 단정도)로 변환 후 전송 |
| `IEEE754_DECODE` | 받은 정수를 다시 **32bit 정수 → 실수**로 복원 |

> 검증값: `ieee754_encode(10.5)=1093140480`, `ieee754_decode(1093140480)=10.5`, `swap_word(10)=655360`. 16bit를 넘는 **정수** 좌표는 `'D'` 타입(06편 `split_word`)으로, **실수**는 `IEEE754_*`로 처리합니다. 자세한 내용은 [부록 B(32bit·IEEE754 변환)](../../appendix/word-conversion.md).

### 6) 그리퍼 레지스터 맵 (매뉴얼 Table 55, XEG-64)
| 영역 | 주소 | 의미 | 값 |
|------|------|------|-----|
| **Holding Register** (R/W) | `1536` | 그리퍼 모델 | 2624 = XEG-64 |
| | `1600` | 방향 | 0=닫기 / 1=열기 |
| | `1601` | 이동 행정 | 단위 0.01 mm (50.00mm = 5000) |
| | `1602` | 이동 속도 | 단위 0.01 mm/s |
| | `1606` | 실행 확정 | 1 쓰면 동작 → 완료 후 **0 자동 복귀** |
| **Input Register** (R) | `769` | 상태 | 0 Idle / 1 Busy / 2 Pos도달 / 3 Hold / 4~7 Alarm |
| | `770` | 현재 위치 | 단위 0.01 mm |
| | `771` | 펌웨어 버전 | major |

> ⚠️ **완료 판정 함정**: `IR[769]==2`(Pos)만 보면 **직전 동작의 상태가 latch** 되어 즉시 통과합니다. 반드시 `IR[769]==2` **그리고** `HR[1606]==0`(실행 플래그가 0으로 자동 리셋)을 **함께** 확인하세요.

### 7) 응용 예제 3종 개요 (매뉴얼 5.4.5)
| 예제 | 대상(Slave) | 연결 | 로봇이 하는 일 |
|------|-------------|------|----------------|
| **① 그리퍼** | XEG-64 전동 그리퍼 | RTU | Holding Register로 방향·행정·실행을 쓰고, Input Register로 상태·위치를 읽어 열기/닫기 — **이 편의 실습** |
| **② 다른 로봇** | 로봇 B | TCP | 로봇 A가 로봇 B의 속도·DO·PTP를 명령 (06편 레지스터 맵을 반대 방향으로) |
| **③ PLC 읽기** | 미쓰비시 FX5U | TCP | 로봇이 PLC의 M(Coil/DInput)·D(I/H Register) 디바이스를 읽고 씀 |

## 예제로 보기

### `src/client_gripper/main.py` : 그리퍼 열기/닫기 사이클
로봇(Master Client) 역할로 그리퍼 모델을 확인하고, 50.00mm 열었다 닫습니다. 매뉴얼 5.4.5.1 예제①의 흐름입니다. (전체 코드는 파일 참조)

```python
from modbus_master import RobotMaster

def run_gripper(m, direction, stroke_001mm=5000, speed_001mm=5000):
    m.write_holding(1600, direction)      # ① 방향 (0=닫기 / 1=열기)
    m.write_holding(1601, stroke_001mm)   # ② 이동 행정 (0.01mm)
    m.write_holding(1602, speed_001mm)    # ③ 이동 속도
    m.write_holding(1606, 1)              # ④ 실행 트리거
    # ⑤ IR769==2 와 HR1606==0 을 함께 확인 (latch 함정 회피)
    while not (m.read_input(769, 1)[0] == 2 and m.read_holding(1606, 1)[0] == 0):
        time.sleep(0.05)
    return m.read_input(769, 1)[0], m.read_input(770, 1)[0]

with RobotMaster(args.host, args.port) as m:          # MBC_TCP_OPEN(1,"...",502)
    model = m.read_holding(1536, 1)[0]                 # MBC_READ_HOLDING ... 'W',1 -> 2624
    run_gripper(m, 1, 5000)                            # 열기 50.00mm
    run_gripper(m, 0, 5000)                            # 닫기
```

## 실행/검증해 보기

### 터미널 A — 그리퍼 서버 띄우기
이 창은 켜둔 채 둡니다.
```powershell
cd lecture/_shared
set PYTHONUTF8=1
python gripper_sim.py --port 1503 --host 127.0.0.1
```
```text
============================================================
 XEG 그리퍼 Modbus SERVER 시뮬레이터  127.0.0.1:1503
 로봇(Client) 대신 modbus_master.py 로 1600/1601/1606 을 써서 제어해 보세요.
 종료: Ctrl+C
============================================================
그리퍼 로직 스레드 시작.
```

### 터미널 B — 로봇(마스터) 사이클 실행
```powershell
cd lecture/06_client/07_modbus_client
set PYTHONUTF8=1
python src/client_gripper/main.py --port 1503
```
예상 출력:
```text
=== 그리퍼 제어 사이클 (로봇 = Master Client) ===
[①] 모델 확인 HR[1536]=2624  ->  XEG-64
[②] 열기 명령: HR[1600]=1, HR[1601]=5000, HR[1606]=1
[③] 열기 완료  IR[769]=2(Pos), IR[770]=5000(= 50.00mm), HR[1606]=0(자동 리셋)
[④] 닫기 명령: HR[1600]=0, HR[1606]=1
[⑤] 닫기 완료  IR[769]=2(Pos), IR[770]=0(= 0.00mm)
그리퍼 제어 사이클 완료 ✅
```

터미널 A(서버)에는 동작 로그가 함께 찍힙니다.
```text
  ▶ 그리퍼 열기 (목표 50.00 mm)
  ✔ 동작 완료: 상태=2(Pos), 위치=50.00 mm
  ▶ 그리퍼 닫기 (목표 0.00 mm)
  ✔ 동작 완료: 상태=2(Pos), 위치=0.00 mm
```

✅ **체크포인트**: `HR[1536]=2624`(XEG-64) 확인 → 열기 후 `IR[769]=2`(Pos), `IR[770]=5000`(= 50.00mm), `HR[1606]`이 **0으로 자동 복귀** → 닫기(`방향=0`) 후 `IR[770]=0`. 로봇이 그리퍼를 **양방향으로 능동 제어**하고 완료를 상태 폴링으로 확인하는 한 사이클을 완주했습니다.

## 자주 하는 실수

### Q. `IR[769]==2` 로 완료를 봤는데 동작이 시작되기도 전에 통과해요.
A. **latch 함정**입니다. 직전 동작이 끝나면 `IR[769]`는 2(Pos)로 **남아 있습니다**. 다음 명령을 보낸 직후에도 잠시 2이므로, 2만 보면 즉시 통과합니다. 그리퍼가 동작 시 스스로 0으로 만드는 `HR[1606]`을 함께 보고, **`IR[769]==2` 그리고 `HR[1606]==0`** 일 때만 완료로 판단하세요.

### Q. 실수 좌표(`10.5`)를 레지스터에 그대로 썼더니 깨져요.
A. **Modbus는 실수를 직접 못 보냅니다.** 전송 전 `IEEE754_ENCODE(10.5)`로 정수(`1093140480`)로 바꿔 보내고, 받는 쪽은 `IEEE754_DECODE`로 복원하세요. 16bit를 넘는 **정수** 좌표는 `'D'` 타입(또는 06편 `split_word`)으로 처리합니다.

### Q. 그리퍼가 안 움직이거나 엉뚱한 위치로 가요.
A. 쓰기 **순서**가 틀렸습니다. 방향(`HR1600`)·행정(`HR1601`)·속도(`HR1602`)를 **먼저** 쓰고, 실행 트리거(`HR1606=1`)는 **마지막**입니다. 트리거가 올라간 순간의 값이 사용됩니다.

### Q. `ConnectionError: 슬레이브에 연결 실패` 가 나요.
A. 그리퍼 서버 미실행 또는 포트 불일치입니다. 터미널 A에 `gripper_sim.py --port 1503`이 떠 있는지, `--port` 인자가 서로 맞는지 확인하세요. (`502` 같은 1024 미만 포트는 권한 문제로 1503을 씁니다.)

## 정리
- 로봇 = **Master Client**. 그리퍼·PLC·다른 로봇의 4종 레지스터를 **능동적으로** 읽고 쓴다. 한 로봇이 **연결 번호 1~4**로 최대 4개 Server와 동시 연결.
- 연결은 `MBC_RTU_OPEN`/`MBC_TCP_OPEN`으로 **먼저** 열고, 데이터는 **Bit 명령**(`READ_DINPUT`/`READ_COIL`/`WRITE_COIL`)과 **Word 명령**(`READ_INPUT`/`READ_HOLDING`/`WRITE_HOLDING`, `'W'`/`'D'`)으로 주고받는다.
- 그리퍼 사이클: 방향·행정 쓰기 → `HR[1606]=1` 트리거 → **`IR[769]==2` 그리고 `HR[1606]==0`** 폴링(latch 함정 회피) → `IR[770]`로 위치 확인.
- **실수는 Modbus로 직접 못 보낸다**: `IEEE754_ENCODE`(실수→정수, `10.5→1093140480`) 후 전송, `IEEE754_DECODE`로 복원. byte order가 반대면 `SWAP_WORD`(`10→655360`).

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[08. 모니터링 & 디버깅](../../07_debug/08_monitoring/README.md) — 06·07편에서 오가는 통신을 **모니터링·디버깅**하는 방법(패킷 관찰, 상태 폴링, 로깅)을 다룹니다.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication User Manual* (C25UE801-2211)
  - **Ch.5.4.1 Functional Application Notes** (p.81, 로봇=Client, 최대 4 Server, 4종 데이터 + 변환)
  - **Ch.5.4.2 Function Interface Setting** (p.82~85, RTU·TCP Client 연결 4종)
  - **Ch.5.4.3 Application Instruction** (p.86~101, Table 54 명령 요약, `MBC_RTU/TCP_OPEN/CLOSE`, `READ/WRITE_*`)
  - **Ch.5.4.4 Data Processing** (p.102~105, SWAP_WORD / IEEE754_ENCODE / IEEE754_DECODE)
  - **Ch.5.4.5 Example Programs** (p.106~116, 예제① XEG 그리퍼 / 예제② 다른 로봇 / 예제③ FX5U PLC, Table 55~56)
- 32bit·IEEE754 변환 실습: [부록 B](../../appendix/word-conversion.md) · `MBC_*` 치트시트: [부록 A](../../appendix/cheatsheet.md)
