# 08. 모니터링 & 디버깅

[06. MODBUS SERVER](../../05_server/06_modbus_server/README.md)에서 로봇은 Server, [07. MODBUS CLIENT](../../06_client/07_modbus_client/README.md)에서 로봇은 Client였습니다. 두 경우 모두 **눈에 보이지 않는 바이트**가 TCP 위를 오갑니다. 통신이 "안 되는데 왜 안 되는지 모르겠다"는 순간, 이 보이지 않는 바이트를 **직접 보고 손으로 해독하는 능력**이 디버깅의 전부입니다. 이번 편은 두 도구로 같은 일을 합니다. 🤖 실장비에서는 **HRSS/Caterpillar Modbus Monitor** 화면으로 송수신 메시지를 보고, 💻 PC에서는 **Wireshark**로 실제 Modbus/TCP 패킷을 캡처합니다. 그리고 하드웨어 없이도 연습할 수 있도록, `src/modbus_monitor/main.py`가 **16진 프레임을 사람이 읽게 풀어 주는 손해독기**로 자동 검증을 제공합니다.

## 학습 목표
- Modbus 패킷이 **`[Function Code][Data]`** 구조이며, 모니터에는 **Slave Address·Function Code·Data**가 16진수로 표시됨을 안다.
- 6종 Function Code(**02h·01h·0Fh·04h·03h·10h**)의 **Master 송신 / Slave 응답 포맷**을 표로 구분하고, raw byte를 **손으로 해독**할 수 있다.
- byte 수 규칙 — **Bit 응답 = ⌈개수/8⌉(올림)**, **Word 응답 = 개수×2** — 으로 응답 길이를 예측한다.
- 🤖 **HRSS/Caterpillar Modbus Monitor** 설정 절차(Expert → Display → Fieldbus → Modbus Monitor, Show message window, Channel/Server, Send/Export)를 수행한다.
- 💻 **Wireshark + Npcap**로 로컬(loopback) Modbus/TCP 트래픽을 캡처하고, 비표준 포트(1502)를 **`Decode As… → Modbus/TCP`**로 강제 해석한다.

## 대상 환경
- 도구: Python 3.10+ (손해독기는 **표준 라이브러리만**, 포트·장비 불필요) / Wireshark + Npcap (라이브 캡처는 선택)
- 플랫폼: Windows PC (시뮬레이션) — 실제 로봇/PLC 불필요. 실장비 측은 HRSS·Caterpillar Modbus Monitor
- 검증: CLI 자동실행 — `python src/modbus_monitor/main.py` (매뉴얼 손계산 예제 3종을 그대로 해독)

## 핵심 개념

### 1) 모니터에 보이는 것은 패킷의 "알맹이"
Modbus 패킷은 운반 방식(RTU vs TCP)에 따라 껍데기가 다르지만, **알맹이(Slave Address + Function Code + Data)**는 동일합니다. 모니터/Wireshark가 보여주는 것이 바로 이 알맹이입니다.
```
 RTU 메시지 :  [Slave Addr][Function Code][      Data      ][ CRC ]
 TCP 메시지 :  [Transaction ID][Protocol ID][Length][Unit ID][Function Code][ Data ]
                └──────────── MBAP 헤더(TCP만) ────────────┘ └── 여기가 핵심 ──┘
```
- **TCP는 CRC가 없습니다**(TCP 계층이 무결성을 보장). RTU는 끝에 **CRC 2바이트**가 붙습니다.
- HRSS/Caterpillar **Modbus Monitor가 표시하는 것**은 위 표의 핵심부, 즉 **Function Code + Data**입니다. 모든 숫자는 **16진수**(끝에 `h`)로 표시되고, 화면에는 **최대 200줄**까지 보입니다.
- Wireshark는 TCP 헤더까지 다 보여주지만, Modbus 디섹터를 켜면 **Function Code / Reference Number / Word·Bit Count / Data**를 분해해 줍니다. 매뉴얼 손계산과 **같은 값**이 나와야 합니다.

### 2) 🤖 HRSS/Caterpillar Modbus Monitor 절차 (매뉴얼 5.5.1)
Wireshark가 없는 현장에서는 컨트롤러 화면으로 같은 정보를 봅니다.
1. 사용자 모드를 **Expert**로 전환 → 메인 메뉴 → **Display** → **Fieldbus** → **Modbus Monitor**.
2. **`Show message window`** 체크 (체크 안 하면 메시지가 표시되지 않음, 화면은 계속 갱신).
3. **Channel**(Channel1/Channel2) 선택. Client 측이면 **Server 번호(1~4)** 선택 후 **`Send`**로 패킷 송신.
4. 화면에 `Send to server` / `Receive from client` 형태로 **16진수 메시지(최대 200줄)**가 뜹니다.
5. 기록을 남기려면 컨트롤러에 **USB** 디스크를 꽂고 **`Export`**로 로그 저장. (Caterpillar는 하단의 *Modbus Monitor* 탭, 이후 절차 동일.)

> 연결/해제도 기록됩니다(예: *Channel1 Modbus TCP server successful connection / disconnection*). `connection`이 안 뜨면 물리/네트워크 문제, `connection` 후 Query는 가는데 `Receive`가 없으면 주소/권한 문제로 좁혀집니다.

### 3) Function Code 6종 — Bit 4개 / Word 2개
| FC | 의미 | 대상 | 방향 |
|----|------|------|------|
| **02h** | Read Discrete Inputs | Discrete Input | 읽기(Bit) |
| **01h** | Read Coils | Coil | 읽기(Bit) |
| **0Fh** | Write Multiple Coils | Coil | 쓰기(Bit) |
| **04h** | Read Input Registers | Input Register | 읽기(Word) |
| **03h** | Read Holding Registers | Holding Register | 읽기(Word) |
| **10h** | Write Multiple Registers | Holding Register | 쓰기(Word) |

> **핵심 규칙 두 가지** — ① **Bit 응답의 byte 수 = ⌈개수/8⌉(올림)**, 8비트가 1바이트. ② **Word 응답의 byte 수 = 개수×2**, 1워드 = 2바이트. 이 둘만 알면 모든 응답 길이를 예측할 수 있습니다.

### 4) Function Code별 송수신 포맷 (Function Code + Data 부분만, 모두 16진수)
| 동작 | 방향 | FC | Data 구조 (바이트) |
|------|------|----|---------------------|
| **Discrete Input 다중읽기** | Master 송신 | 02h | `[시작주소(2)]` `[개수(2)]` |
| | Slave 응답 | 02h | `[byte수(1)]` `[비트상태(byte수×1)]` |
| **Coil 다중읽기** | Master 송신 | 01h | `[시작주소(2)]` `[개수(2)]` |
| | Slave 응답 | 01h | `[byte수(1)]` `[비트상태(byte수×1)]` |
| **Coil 다중쓰기** | Master 송신 | 0Fh | `[시작주소(2)]` `[개수(2)]` `[byte수(1)]` `[비트상태]` |
| | Slave 응답 | 0Fh | `[시작주소(2)]` `[개수(2)]` |
| **Input Register 다중읽기** | Master 송신 | 04h | `[시작주소(2)]` `[개수(2)]` |
| | Slave 응답 | 04h | `[byte수(1)]` `[레지스터값(=개수×2)]` |
| **Holding Register 다중읽기** | Master 송신 | 03h | `[시작주소(2)]` `[개수(2)]` |
| | Slave 응답 | 03h | `[byte수(1)]` `[레지스터값(=개수×2)]` |
| **Holding Register 다중쓰기** | Master 송신 | 10h | `[시작주소(2)]` `[개수(2)]` `[byte수(1)]` `[레지스터값(=개수×2)]` |
| | Slave 응답 | 10h | `[시작주소(2)]` `[개수(2)]` |

> **읽기**는 Master가 "어디서 몇 개"만 보내고 Slave가 데이터를 돌려줍니다. **쓰기**(0Fh·10h)는 Master 송신에 **데이터까지** 실리고, Slave 응답은 "시작주소+개수"만 **에코**합니다(쓴 데이터는 다시 안 보냄). 응답 FC의 **최상위 비트가 1**(예: 02h→82h)이면 **에러 응답**이고 다음 1바이트가 **Exception Code**(02h 잘못된 주소 / 03h 잘못된 값 / 01h 미지원 기능)입니다.

### 5) 손계산 예제 3종 (매뉴얼 원문 그대로)
회색 규칙(Bit=⌈개수/8⌉, Word=개수×2)을 적용해 직접 해독합니다.

**① 02h — Discrete Input 다중읽기 (요청)**
```
 02 01 2C 00 05
   02h    → Function Code: Read Discrete Inputs
   01 2C  → 시작주소 = 0x012C = 300
   00 05  → 개수 = 5
```

**② 04h — Input Register 다중읽기 (응답)**
```
 04 04 00 5A 00 00
   04    → FC 04h Read Input Registers
   04    → byte 수 = 2 × 2 = 4  → 레지스터 2개
   00 5A → 0x005A = 90   (첫 레지스터)
   00 00 → 0x0000 = 0    (둘째 레지스터)
```

**③ 10h — Holding Register 다중쓰기 (요청)**
```
 10 00 C9 00 03 06 00 6F 00 DE 01 4D
   10h    → Write Multiple Registers
   00 C9  → 시작주소 = 0x00C9 = 201
   00 03  → 개수 = 3
   06     → byte 수 = 3 × 2 = 6
   00 6F  → 0x006F = 111
   00 DE  → 0x00DE = 222
   01 4D  → 0x014D = 333
 (Slave 응답은 10 00 C9 00 03 — 시작주소+개수만 에코, 데이터 생략)
```

## 예제로 보기

### `src/modbus_monitor/main.py` : Modbus 프레임 손해독기
16진 프레임을 입력하면 Function Code·시작주소·개수·byte수·데이터를 사람이 읽게 풉니다. 표준 라이브러리만 쓰고 포트가 필요 없어, 모니터/Wireshark에서 본 byte를 그대로 검증하는 데 씁니다. (전체 코드는 파일 참조)

```python
# 핵심부 — FC별로 필드를 해석하고, 읽기 응답은 byte수만큼 16bit 값으로 합친다
FC_NAMES = {0x02: "Read Discrete Inputs", 0x04: "Read Input Registers",
            0x10: "Write Multiple Registers", ...}

def decode_frame(text, kind="auto"):
    data = parse_hex(text)            # '02 01 2C 00 05' -> [0x02,0x01,0x2C,0x00,0x05]
    fc = data[0]
    # 요청(읽기): [시작주소(2)][개수(2)]
    start = (data[1] << 8) | data[2]  # 0x012C = 300
    count = (data[3] << 8) | data[4]  # 5
    # 응답(Word 읽기): [byte수(1)][레지스터값...] -> 값 = (hi<<8)|lo
    ...

decode_frame("02 01 2C 00 05", "request")   # FC=02h, 시작주소 300, 개수 5
decode_frame("04 04 00 5A 00 00", "response")  # byte수 4, 값 [90, 0]
decode_frame("10 00 C9 00 03 06 00 6F 00 DE 01 4D", "request")  # 주소 201, 값 [111,222,333]
```

## 실행/검증해 보기

### CLI 자동 검증 (하드웨어·포트 불필요)
```powershell
cd lecture/07_debug/08_monitoring
set PYTHONUTF8=1
python src/modbus_monitor/main.py
```
예상 출력:
```
=== Modbus 프레임 손해독기 ===
--- ① 요청 02h ---
입력 프레임: 02 01 2C 00 05
  FC=0x02 (Read Discrete Inputs)
  시작주소 = 0x012C = 300
  개수     = 5

--- ② 응답 04h ---
입력 프레임: 04 04 00 5A 00 00
  FC=0x04 (Read Input Registers)
  byte 수  = 4
  값(10진) = [90, 0]

--- ③ 요청 10h ---
입력 프레임: 10 00 C9 00 03 06 00 6F 00 DE 01 4D
  FC=0x10 (Write Multiple Registers)
  시작주소 = 0x00C9 = 201
  개수     = 3
  byte 수  = 6
  값(10진) = [111, 222, 333]
------------------------------
프레임 해독 검증 통과 ✅
```

✅ **체크포인트**: 세 프레임이 각각 **시작주소 300**, **값 [90, 0]**, **시작주소 201 / 값 [111, 222, 333]**로 풀리고 마지막 줄이 `프레임 해독 검증 통과 ✅`, 종료 코드 0이면 매뉴얼 손계산과 코드가 일치한 것입니다.

### 💻 Wireshark 라이브 캡처 절차 (선택)
실제 패킷도 같은 byte로 보이는지 확인하려면 시뮬레이터로 트래픽을 만들어 캡처합니다.

**터미널 1** — 로봇 Server를 **1502** 포트로 띄웁니다(켜둔 채로).
```powershell
cd lecture/_shared
set PYTHONUTF8=1
python robot_server_sim.py --port 1502 --host 127.0.0.1
```

**Wireshark 사전 설정** (반드시 먼저!) — 로컬(127.0.0.1 ↔ 127.0.0.1) 통신은 물리 랜카드를 거치지 않습니다.
1. **Npcap 설치** — Wireshark 설치 마법사에서 *Install Npcap* 체크(loopback 캡처 필수).
2. **캡처 인터페이스** — 시작 화면에서 **`Adapter for loopback traffic capture`**(또는 `Npcap Loopback Adapter`)를 더블클릭.
3. **표시 필터** — 상단 바에 `tcp.port == 1502` 입력 후 Enter.

**터미널 2** — Master로 Discrete Input 8개를 읽어 트래픽을 만듭니다.
```powershell
cd lecture/_shared
python modbus_master.py --port 1502 read-di 0 8
```
```text
[0, 0, 0, 1, 0, 0, 0, 0]
```

4. **비표준 포트 디코딩** — Wireshark는 **TCP 502**만 Modbus로 자동 해석합니다. 잡힌 패킷을 우클릭 → **`Decode As…`** → 포트(1502) 행의 *Current* 열을 **`Modbus/TCP`**로 지정 → OK.

Query/Response 2개 패킷이 잡히고, 상세 트리를 펼치면 손해독기와 같은 값이 보입니다.

| 패킷 | Wireshark 표시 | raw 의미 |
|------|----------------|----------|
| Query (→Server) | Func **2 Read Discrete Inputs** / Reference **0** / Bit Count **8** | `02 00 00 00 08` |
| Response (←Server) | Func **2** / Byte Count **1** / Data **0x08** | `02 01 08` |

`0x08 = 0b0000 1000` → 주소 0~7 중 **주소 3만 On** → CLI 출력 `[0,0,0,1,0,0,0,0]`와 일치합니다. 이 raw byte를 손해독기에 넣어 확인할 수도 있습니다(`decode_frame("02 01 08", "response")`).

> 여러 값을 쓰는 명령(예: 06장 `write_holding(201, [111,222,333])`)을 실행하면 실습 ③의 `10 00 C9 00 03 06 …` 패킷을 직접 캡처해 손해독기로 풀 수 있습니다.

## 자주 하는 실수

### Q. Wireshark에 패킷이 전혀 안 잡혀요(127.0.0.1 ↔ 127.0.0.1).
A. 로컬 통신은 물리 랜카드를 거치지 않습니다. 캡처 인터페이스를 **`Adapter for loopback traffic`**(Npcap Loopback)로 바꾸세요. 목록에 없으면 Wireshark 재설치 시 **Npcap + loopback** 옵션을 체크합니다.

### Q. 패킷은 잡히는데 Protocol 컬럼이 `Modbus/TCP`가 아니라 `TCP`로만 나와요.
A. Wireshark는 **502 포트만** Modbus로 자동 해석합니다. 실습은 1502이므로 패킷 우클릭 → **`Decode As…`** → 포트 1502를 **`Modbus/TCP`**로 지정하세요.

### Q. byte 수와 레지스터 개수를 자꾸 헷갈려요.
A. **Word는 1개당 2바이트**입니다. 응답의 두 번째 바이트가 byte 수이고, 레지스터 개수는 `byte수 ÷ 2`입니다. 예: `04 04 00 5A 00 00`은 byte 4 → 레지스터 **2개**([90, 0]). Bit는 반대로 `⌈개수/8⌉`로 **올림**합니다.

### Q. 응답 FC가 `0x82`, `0x83`처럼 나와요.
A. **에러 응답**입니다. FC 최상위 비트가 1로 켜진 것이고, 바로 다음 바이트가 **Exception Code**입니다(02h Illegal Data Address=범위 밖 주소, 03h Illegal Data Value=잘못된 개수/값, 01h Illegal Function=미지원 기능). 주소·길이·지원 여부를 확인하세요.

## 정리
- Modbus 패킷의 알맹이는 **`[Function Code][Data]`**. 모니터/Wireshark에 **16진수**로 보이며, HRSS 모니터는 **최대 200줄** 표시.
- 6종 FC: 읽기 **02h(DI)·01h(Coil)·04h(IR)·03h(HR)**, 쓰기 **0Fh(Coil)·10h(HR)**. **읽기 응답엔 데이터**, **쓰기 응답엔 시작주소+개수 에코**.
- 길이 규칙: **Bit 응답 byte = ⌈개수/8⌉**, **Word 응답 byte = 개수×2**. 매뉴얼 예제 `02 01 2C 00 05`, `04 04 00 5A 00 00`, `10 00 C9 00 03 06 …`를 손해독기로 검증.
- 🤖 **HRSS/Caterpillar Modbus Monitor**: Expert → Display → Fieldbus → Modbus Monitor, **Show message window**, Channel/Server 선택 후 Send, **USB Export**.
- 💻 **Wireshark**: Npcap + loopback 어댑터, 비표준 포트는 **Decode As → Modbus/TCP**, 필터 `tcp.port == 1502`. 캡처한 raw byte의 시작주소·개수·데이터가 명령과 일치함을 확인.

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[09. 종합 실습](../../08_capstone/09_cell/README.md) — I/O·TCP·RS232·Modbus(Server/Client)·모니터링을 하나로 묶어 **실전 통합 셀 시나리오**를 구성합니다.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication User Manual* (C25UE801-2211)
  - **Ch.5.5 MODBUS Transmission Status Monitoring** — p.117 (모니터 개요, 패킷 구조, 200줄/16진수)
  - **Ch.5.5.1 Monitoring Function Interface Setting** — p.118~119 (HRSS / Caterpillar: Expert→Display→Fieldbus→Modbus Monitor, Show message window, Channel/Server, Send, USB Export)
  - **Ch.5.5.2 Transmission Status Message Specifications** — p.120~127 (Table 57 송수신 포맷, 5.5.2.1 연결/해제, 02h/01h/0Fh/04h/03h/10h, 손계산 예제)
- Function Code 치트시트: [부록 A](../../appendix/cheatsheet.md) · Word/32bit 변환: [부록 B](../../appendix/word-conversion.md)
- 공유 시뮬레이터: [`_shared/robot_server_sim.py`](../../_shared/robot_server_sim.py) · 마스터 CLI: [`_shared/modbus_master.py`](../../_shared/modbus_master.py)
