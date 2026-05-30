# 05. MODBUS 기초

RS-232([04편](../../03_network/04_rs232/README.md))가 두 장치를 1:1로 잇는 점대점 통신이었다면, **MODBUS**는 한 대의 마스터가 여러 슬레이브를 **레지스터(register) 단위**로 읽고 쓰는 산업 표준 프로토콜입니다. PLC가 로봇을 제어하거나, 로봇이 전동 그리퍼·센서를 다룰 때 모두 이 방식을 씁니다. 이번 편은 **PC만으로** 가상 슬레이브를 띄우고, 마스터로 4종 레지스터와 Function Code를 직접 읽고/써 봅니다.

## 학습 목표
- MODBUS의 **Master(Client) ↔ Slave(Server)** 요청/응답 구조를 설명한다.
- **Modbus RTU와 Modbus TCP**의 물리 계층·에러 검증 차이를 비교하고, HIWIN 로봇이 RTU에 **RS485**를 쓰는 이유를 안다.
- 4종 레지스터(**Discrete Input, Coil, Input Register, Holding Register**)의 비트 폭·읽기/쓰기 권한·값 범위를 구분한다.
- 주요 **Function Code(01~06, 15, 16)** 가 어떤 레지스터를 읽고 쓰는지 매핑한다.
- `RobotMaster`로 4종 레지스터를 직접 읽고/쓰며, 읽기 전용 레지스터에는 쓸 수 없음을 확인한다.

## 대상 환경
- 도구: Python 3.10+ / pymodbus 3.6.9
- 플랫폼: Windows PC (시뮬레이션) — 실제 로봇/PLC 불필요
- 검증: 터미널 A에 슬레이브 + 터미널 B에 `python src/modbus_basics/main.py`

## 핵심 개념

### 1) MODBUS 개요 — Master와 Slave
MODBUS는 산업 현장에서 가장 널리 쓰이는 Fieldbus 프로토콜의 하나로, **Master(Client)** 와 **Slave(Server)** 로 구성됩니다.

- **Master(Client)** 가 **요청(Demand)** 을 보냅니다. ("HR[100] 값을 줘", "Coil[300]을 1로 써")
- **Slave(Server)** 는 요청에 **응답(Response)** 합니다. 모든 슬레이브가 명령을 수신하지만, **지정된 주소(Address)** 를 가진 장치만 실행·응답합니다.

```
   ┌──────────┐   Demand(요청) ─────►   ┌──────────┐
   │  Master  │                          │  Slave   │
   │ (Client) │   ◄───── Response(응답)  │ (Server) │
   └──────────┘                          └──────────┘
   PLC / 상위 PC                          로봇 / 그리퍼 / 센서
```

> HIWIN 로봇은 **마스터** 가 될 수도(그리퍼·센서 제어), **슬레이브** 가 될 수도(PLC가 로봇을 제어) 있습니다. 이번 편은 로봇을 **슬레이브** 로 두고 PC 마스터로 접속합니다. 로봇을 슬레이브로 두고 명령 사이클을 돌리는 실습은 [06. MODBUS SERVER](../../05_server/06_modbus_server/README.md)에서 다룹니다.

### 2) Modbus RTU vs Modbus TCP
MODBUS에는 RTU, TCP, ASCII 세 형식이 있으며, HRSS는 **RTU와 TCP** 를 지원합니다.

| 구분 | **Modbus RTU** | **Modbus TCP** |
|------|----------------|----------------|
| 물리 계층 | 시리얼 — **RS485**(HIWIN), RS232/RS422도 가능 | **Ethernet**(LAN/RJ45) |
| 데이터 표현 | **Binary**(이진) 전송 | TCP/IP 패킷에 MODBUS 데이터를 **캡슐화** |
| 에러 검증 | 데이터 끝에 **CRC** 코드 필수 | **TCP 계층이 검증** → CRC 불필요 |
| HIWIN 사용 | **RS485 전송** | Ethernet 전송 |

> **CRC**(Cyclic Redundancy Check, 순환 중복 검사): 데이터로부터 짧은 고정 길이 검증 코드를 만들어 덧붙이고, 수신 측이 다시 계산해 변형 여부를 확인합니다. RTU는 시리얼 raw 전송이라 CRC가 **필수** 지만, TCP는 하위 TCP 계층이 무결성을 보장하므로 MODBUS 레벨의 CRC가 **생략** 됩니다.
>
> 💡 본 실습은 PC 1대에서 진행하므로 **Modbus TCP**(`127.0.0.1`)를 씁니다. 데이터 모델(4종 레지스터·Function Code)은 RTU와 **완전히 동일** 하므로, 여기서 익힌 개념이 RS485 RTU에 그대로 적용됩니다.

### 3) 4종 데이터 레지스터
Function Code가 다루는 데이터는 슬레이브 내부에 4종 레지스터로 저장됩니다. **비트 폭과 읽기/쓰기 권한** 이 핵심입니다.

| 레지스터 | 비트 폭 | 권한 | 값 범위 | 비고 |
|----------|---------|------|---------|------|
| **Discrete Input** | 1 bit | **읽기 전용(R)** | 0 ~ 1 | 외부 입력 신호(예: 로봇 상태 출력 SO) |
| **Coil** | 1 bit | **읽기/쓰기(R/W)** | 0 ~ 1 | ON/OFF 제어(예: 입력 신호 SI, 디지털 출력 DO) |
| **Input Register** | 16 bit word | **읽기 전용(R)** | -32768 ~ 32767 | 측정값·상태값(예: 속도%, 동작 상태) |
| **Holding Register** | 16 bit word | **읽기/쓰기(R/W)** | -32768 ~ 32767 | 설정값·파라미터(예: 속도 설정, 명령 번호) |

> 16비트 word는 2¹⁵=32768 기준으로 -32768~32767을 표현합니다. 데이터가 16비트를 넘으면(예: 좌표값) 두 word(L/H)로 나눠 32비트로 합칩니다 — 변환법은 [부록(MODBUS 계산)](../../appendix/word-conversion.md)과 [06. MODBUS SERVER](../../05_server/06_modbus_server/README.md)에서 다룹니다.

### 4) Function Code
마스터는 **어떤 레지스터를 읽고 쓸지** 를 Function Code로 지정합니다.

| Function Code | 기능 | 대상 레지스터 | 읽기/쓰기 |
|:---:|------|---------------|:---:|
| **01** | Read Coil status | Coil | 읽기 |
| **02** | Read Discrete Input status | Discrete Input | 읽기 |
| **03** | Read Holding Register | Holding Register | 읽기 |
| **04** | Read Input Register | Input Register | 읽기 |
| **05** | Write **single** Coil | Coil | 쓰기 |
| **06** | Write **single** Holding Register | Holding Register | 쓰기 |
| **15** | Write **multiple** Coil | Coil | 쓰기 |
| **16** | Write **multiple** Holding Register | Holding Register | 쓰기 |

> 규칙이 보이나요? **01/02 = 비트(Coil/DI) 읽기**, **03/04 = word(HR/IR) 읽기**, **05/06 = 단일 쓰기**, **15/16 = 다중 쓰기**. 그리고 **읽기 전용인 Discrete Input·Input Register에는 쓰기 Function Code가 없습니다**(02·04만 존재). 이것이 권한 차이의 핵심입니다.

### 5) MODBUS 데이터 구조 — 4부
마스터가 보내는 명령 데이터는 다음 4부분으로 구성됩니다.

| # | 부분 | 역할 |
|---|------|------|
| ① | **(Slave) Address** | 모든 슬레이브가 수신하지만, 이 주소를 가진 장치만 실행·응답 |
| ② | **Function code** | 명령의 기능(어떤 레지스터를 읽을지/쓸지) 지정 |
| ③ | **Data** | 레지스터 값, 읽을 개수, 쓸 값 등 실제 내용 |
| ④ | **Error check** | 명령 무결성 확인용 검증 코드(**CRC**) — **Modbus TCP에서는 생략** |

## 예제로 보기

### 예제 — `src/modbus_basics/main.py` : 4종 레지스터 직접 다루기
`from modbus_master import RobotMaster` 로 마스터를 만들고, 4종 레지스터를 각각 읽은 뒤(02/01/04/03) R/W 권한이 있는 Holding(06)·Coil(05)에 써넣고 다시 읽어 반영을 확인합니다. (전체 코드는 파일 참조)

```python
# 핵심부 — 읽기(02·01·04·03) 후 쓰기(06·05) 하고 되읽어 확인
with RobotMaster(args.host, args.port, args.unit) as m:
    di = [int(b) for b in m.read_discrete(0, 8)]   # FC02 Discrete Input
    co = [int(b) for b in m.read_coils(0, 8)]       # FC01 Coil
    ir = m.read_input(524, 1)[0]                     # FC04 Input Register(동작상태)
    hr = m.read_holding(100, 1)[0]                   # FC03 Holding Register(속도설정)

    m.write_holding(100, 50)                         # FC06 Holding 쓰기
    assert m.read_holding(100, 1) == [50]           # 되읽어 확인

    m.write_coil(300, 1)                             # FC05 Coil 쓰기(DO1 ON)
    assert [int(b) for b in m.read_coils(300, 1)] == [1]
```

> 💡 `read_*` 계열은 항상 **리스트** 를 돌려줍니다. 비트형(DI·Coil)은 `[0, 1, ...]`, word형(IR·HR)은 정수 리스트입니다. 단일 값은 `[0]` 으로 꺼냅니다. **읽기 전용** 인 Input Register·Discrete Input 에는 `write_input`/`write_discrete` 메서드가 **아예 없습니다**(읽기 전용 강제).

## 실행/검증해 보기

**터미널 A** — 슬레이브(로봇 서버)를 띄우고 그대로 둡니다.

```powershell
cd lecture/04_modbus/05_modbus_basics
python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1
```

```text
============================================================
 로봇 Modbus SERVER 시뮬레이터  127.0.0.1:1502  (Slave ID 1)
 마스터(modbus_master.py / QModMaster)로 접속해 명령 사이클을 실습하세요.
 종료: Ctrl+C
============================================================
로봇 로직 스레드 시작.
```

**터미널 B** — 마스터 데모를 실행합니다.

```powershell
cd lecture/04_modbus/05_modbus_basics
python src/modbus_basics/main.py --port 1502
```

예상 출력:
```
=== MODBUS 기초 — 4종 레지스터 직접 다루기 ===
슬레이브 127.0.0.1:1502 (Slave ID 1) 에 접속합니다.

[읽기] 4종 레지스터를 각각 읽습니다.
  ① Discrete Input (FC02) read_discrete(0,8) = [0, 0, 0, 1, 0, 0, 0, 0]
     -> 주소 3(SO4=Ready)만 1. 로봇이 '준비됨' 상태입니다.
  ② Coil           (FC01) read_coils(0,8)    = [0, 0, 0, 0, 0, 0, 0, 0]
     -> SI1~SI8(입력). 아직 켜지 않아 전부 0.
  ③ Input Register (FC04) read_input(100,1)  = [100]  (속도%)
                          read_input(524,1)  = [1]  (동작상태 1=Idle)
  ④ Holding Reg    (FC03) read_holding(100,1)= [0]  (속도 설정값)

[쓰기] R/W 권한을 가진 Holding Register / Coil 에 값을 씁니다.
  ⑤ Holding 쓰기 (FC06) write_holding(100, 50)
     재확인 read_holding(100,1) = [50]  ✅
  ⑥ Coil 쓰기    (FC05) write_coil(300, 1)  (DO1 ON)
     재확인 read_coils(300,1) = [1]  ✅

------------------------------
4종 레지스터 읽기/쓰기 데모 완료 ✅
```

✅ **체크포인트**: 네 가지 읽기가 각각 **02 / 01 / 04 / 03** Function Code에 대응하고, 쓰기 후 재확인 줄이 모두 `✅` 이면, "주소 + Function Code + 데이터" 의 조합으로 슬레이브를 다루는 데 성공한 것입니다.

## 자주 하는 실수

### Q. `ConnectionError: 슬레이브에 연결 실패`
A. 터미널 A의 슬레이브가 떠 있지 않거나 포트가 다릅니다. `robot_server_sim.py --port 1502` 가 실행 중인지, 마스터도 `--port 1502` 로 맞췄는지 확인하세요.

### Q. `read_input(524)`(Input Register)에 값을 쓰려는데 메서드가 없어요.
A. 버그가 아니라 **설계** 입니다. Input Register와 Discrete Input은 **읽기 전용** 이라 쓰기 Function Code 자체가 없고, `RobotMaster` 에도 `write_input`/`write_discrete` 가 **없습니다**. 슬레이브(로봇)가 채우는 값이므로 마스터는 읽기만 합니다.

### Q. `read_holding(100, 1)` 결과 `[50]` 이 정수 `50` 과 같다고 비교했더니 False예요.
A. `read_*` 는 항상 **리스트** 를 돌려줍니다. 단일 값은 `m.read_holding(100, 1)[0]` 처럼 `[0]` 으로 꺼내서 비교하세요.

### Q. 값을 썼는데 다음 실행에서 0이 아니라 이전 값이 보여요.
A. 슬레이브는 켜져 있는 동안 레지스터 상태를 **유지** 합니다. 초기값으로 되돌리려면 터미널 A에서 Ctrl+C 후 슬레이브를 재시작하세요.

## 정리
- MODBUS는 **Master(요청) ↔ Slave(응답)** 구조이며, 명령은 **① Address ② Function code ③ Data ④ Error check(CRC, TCP는 생략)** 4부로 구성된다.
- **RTU = RS485 + Binary + CRC 필수**, **TCP = Ethernet + 캡슐화 + TCP가 검증**. HIWIN은 RTU에 **RS485** 를 쓴다.
- 4종 레지스터는 **비트형(DI=R, Coil=R/W)** 과 **word형(IR=R, HR=R/W, -32768~32767)** 으로 나뉘고, 권한이 실제로 강제된다.
- Function Code는 **01/02=비트 읽기, 03/04=word 읽기, 05/06=단일 쓰기, 15/16=다중 쓰기** 로 규칙적이며, 읽기 전용 레지스터에는 쓰기 코드가 없다.

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[06. MODBUS SERVER](../../05_server/06_modbus_server/README.md) — 레지스터 하나하나를 넘어, 로봇을 **슬레이브로 두고 PLC처럼 명령 사이클**(트리거 → 동작 → 완료 확인)을 돌려봅니다.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication User Manual* (C25UE801-2211)
  - **Ch.5.1 MODBUS Communication Specifications** — p.37~38 (Master/Slave 구조, RTU/TCP 비교, CRC, 데이터 구조 4부, 4종 레지스터)
  - **Ch.5.2 MODBUS Communication main structure** — p.39~40 (Function code, 마스터/슬레이브 역할, RS485/Ethernet 배선)
