# 04. RS-232 직렬 통신

RS-232는 로봇과 호스트(PC·PLC)를 **케이블 한 가닥으로 1:1 연결**하는 가장 오래된 직렬 통신입니다. 앞 편 [03. TCP/IP](../03_tcpip/README.md)에서 익힌 `CWRITE`/`CREAD`와 `{ }`·`,` 패킷 포맷이 시리얼에서도 **그대로** 쓰이고, 바뀌는 것은 물리 계층과 `COPEN`의 첫 인자(`ETH` → `SER`)뿐임을 손으로 확인합니다. 가상 COM 포트는 자동 검증 환경에 없으므로, 핵심인 **패킷 프레이밍**은 포트 없이 순수 Python으로 재현하고, 실제 시리얼 송수신은 com0com으로 직접 실습합니다.

## 학습 목표
- RS-232의 물리적 특성(**1:1 점대점**, **TX↔RX 교차 배선 + 공통 GND**, **양측 동일 baud rate**)을 설명한다.
- `COPEN(SER, HANDLE)`의 첫 인자가 시리얼을 뜻하는 `SER`임을 알고, TCP/IP의 `ETH`와 구분한다.
- `{ }`로 감싸고 `,`로 구분하는 패킷의 encode/decode를 작성하고, non-format(ASCII decimal)과 비교한다.
- com0com 가상 COM 포트 쌍(`COM5↔COM6`)을 만들어 pyserial 에코 서버·클라이언트를 동작시킨다.

## 대상 환경
- 도구: Python 3.10+ / pyserial 3.5
- 가상 하드웨어: **com0com**(오픈소스 가상 COM 포트 드라이버) — 실제 케이블·로봇 불필요
- 검증: CLI 자동실행 — `python src/serial_comm/main.py` (포트 불필요)

## 핵심 개념

### 1) RS-232는 두 장치만 잇는 1:1 점대점
이더넷처럼 여러 노드가 한 선을 공유하지 않고, **두 장치만** 한 케이블로 직접 연결합니다. 배선의 핵심은 **TX↔RX 교차(cross)** 입니다. 로봇의 **송신핀(TX)** 을 호스트의 **수신핀(RX)** 에, 로봇의 **수신핀(RX)** 을 호스트의 **송신핀(TX)** 에 잇고, 양측의 **공통 접지(GND)** 를 연결합니다.

```
   로봇 컨트롤러            호스트(PC/PLC)
     TX  ─────────────────►  RX
     RX  ◄─────────────────  TX     ← 교차(cross)
     GND ─────────────────  GND     ← 공통 접지
```

**baud rate(통신 속도)는 양측이 반드시 동일해야** 합니다. 이더넷처럼 자동 협상이 없으므로, 한쪽만 9600·다른 쪽이 19200이면 글자가 깨지거나 통신이 안 됩니다 — **수동으로** 맞춰야 합니다.

### 2) 명령어 — TCP/IP와 거의 동일, 첫 인자만 다름
`COPEN → CWRITE → CREAD` 흐름은 [03. TCP/IP](../03_tcpip/README.md)와 똑같습니다. **딱 한 가지**, `COPEN`의 첫 인자만 `ETH`에서 `SER`로 바뀝니다.

```text
COPEN(SER, HANDLE)                          ; 시리얼 포트 열기 (TCP/IP는 ETH)
CWRITE(HANDLE, SendData1, SendData2)        ; 송신 — TCP/IP와 동일
CREAD(HANDLE, receiveData1, receiveData2)   ; 수신 — TCP/IP와 동일
```

### 3) 패킷 포맷 — TCP/IP와 공통
| 항목 | 규칙 | 예시 |
|------|------|------|
| 시작/끝 기호 | 패킷 앞뒤를 **중괄호 `{` `}`** 로 감쌈 | `123,456` → `{123,456}` |
| 구분 기호 | 여러 데이터는 **콤마 `,`** 로 구분 | `{123,456}` |
| non-format | 포맷을 끄면 시작/끝·구분 기호 없이 데이터를 **ASCII CODE(10진수)** 로 1바이트씩 해석 | `"AB"` → `[65, 66]` |
| Show message | 통신 내용을 화면 대화창에 표시. 테스트 전 **반드시 체크**(기본값은 미표시) | — |

### 4) TCP/IP(03편) vs RS-232 한눈에 비교
| 구분 | **TCP/IP** (03편) | **RS-232** (이번 편) |
|------|-------------------|----------------------|
| `COPEN` 첫 인자 | `ETH` | `SER` |
| 물리 계층 | 이더넷(LAN, RJ45) | 직렬 케이블(D-sub 9핀) |
| 연결 방식 | 다대다·네트워크(IP/Port) | **1:1 점대점** |
| 배선 핵심 | 허브/스위치 경유 | **TX↔RX 교차 + 공통 GND** |
| 거리·속도 | 길고 빠름(수십~수백 Mbps) | 짧고 느림(대략 15 m 이내, 9600~115200 bps) |
| 속도 협상 | 자동 | **수동(양측 baud 동일 설정)** |
| 패킷 포맷 | `{ }`, `,`, non-format | **동일** |

> 핵심: **명령어와 패킷 포맷은 같고, 물리 계층과 `COPEN` 첫 인자만 다릅니다.**

## 환경 준비

```powershell
# 1) pyserial 설치 (최초 1회) — 콘솔 실습 시 필요. 패킷 데모 자체는 표준 라이브러리만 씀
python -m pip install pyserial

# 2) 콘솔 한글 깨짐 방지 (매 세션)
set PYTHONUTF8=1           # PowerShell: $env:PYTHONUTF8=1
```

### com0com 가상 COM 포트 쌍(COM5↔COM6) 만들기
> 💻 **PC 시뮬레이션** — 실제 케이블 없이, **한쪽에 쓰면 다른 쪽에서 읽히는** 가상 포트 쌍을 만듭니다. 이것이 RS-232 크로스 케이블을 소프트웨어로 대신합니다. (콘솔 시리얼 실습에만 필요하며, `src/serial_comm/main.py` 실행에는 불필요합니다.)

1. **com0com 설치**: [com0com](https://sourceforge.net/projects/com0com/)(오픈소스) 설치 프로그램을 받아 실행합니다. 서명 안 된 드라이버 경고가 나오면 설치를 허용합니다.
2. **포트 쌍 생성**: 시작 메뉴의 **"Setup Command Prompt (com0com)"** 또는 GUI **"Setup"** 을 엽니다. 기본 `CNCA0 ↔ CNCB0` 쌍을 **COM5 ↔ COM6** 으로 이름을 바꿉니다.
   - GUI: 두 항목의 포트 이름 칸에 각각 `COM5`, `COM6` 입력 후 **Apply**.
   - 명령창: `change CNCA0 PortName=COM5` 후 `change CNCB0 PortName=COM6`.
3. **확인**: 장치 관리자(Device Manager) → **"포트(COM & LPT)"** 아래에 **COM5와 COM6** 두 포트가 보이면 성공입니다.

> 💡 COM5/COM6이 이미 쓰이고 있으면 비어 있는 다른 번호(예: COM7/COM8)를 쓰고, 이후 명령의 포트 번호만 바꾸면 됩니다.

## 예제로 보기

### 예제 — `src/serial_comm/main.py` : 패킷 프레이밍 데모 (포트 불필요)
RS-232 패킷 포맷의 encode/decode를 순수 Python으로 구현해, 예시 값으로 왕복(round-trip) 검증합니다. (전체 코드는 파일 참조)

```python
# 핵심부 — { } 로 감싸고 , 로 구분 (CWRITE/CREAD 가 쓰는 포맷)
def encode_packet(values):
    return "{" + ",".join(str(v) for v in values) + "}"     # [123,456] -> "{123,456}"

def decode_packet(packet):
    body = packet.strip().strip("{}")                        # 앞뒤 { } 제거
    return [int(tok) for tok in body.split(",")]             # "{123,456}" -> [123,456]

# non-format — 시작/끝·구분 기호 없이 ASCII CODE(10진수) 1바이트씩
encode_nonformat = lambda text: [ord(ch) for ch in text]    # "AB" -> [65, 66]
```

🤖 위 Python 흐름은 실장비 HRSS 코드와 **1:1로 대응**됩니다. 03편 TCP/IP에서 본 표와 비교하면 `ETH`만 `SER`로 바뀝니다.

| 단계 | 💻 PC (Python) | 🤖 실장비 (HRSS RS-232) |
|------|----------------|--------------------------|
| 포트 열기 | `serial.Serial('COM5', 9600, timeout=1)` | `COPEN(SER, HANDLE)` |
| 송신 | `ser.write(encode_packet([123,456]))` | `CWRITE(HANDLE, SendData1, ...)` |
| 수신 | `decode_packet(ser.read(64))` | `CREAD(HANDLE, receiveData1, ...)` |
| 닫기 | `ser.close()` | `CCLOSE(HANDLE)` |
| 사전 설정 | 양쪽 `--baud 9600` 동일 | `Startup Settings → RS-232`에서 baud를 호스트와 동일하게, "Show message" 체크 |

### 💻 com0com 하드웨어 실습 (선택) — 실제 시리얼 송수신
가상 포트 쌍을 만들었다면, 공유 코드로 실제 시리얼 왕복을 실습할 수 있습니다.

**터미널 A** — 에코 서버(호스트 역할, COM6). 수신 데이터를 `{ }`로 감싸 되돌립니다.
```powershell
python ../../_shared/serial_echo.py --port COM6 --baud 9600
```
**터미널 B** — 로봇 클라이언트(로봇 역할, COM5). `{123}`을 보내고 응답을 받습니다.
```powershell
python ../../_shared/serial_client.py --port COM5 --baud 9600 --value 123
```
클라이언트 터미널에 `수신 b'{{123}}'`(에코 서버가 `{ }`로 한 번 더 감쌈)이 찍히면 성공입니다. **양쪽 `--baud`가 같아야** 하며, 한쪽만 19200으로 바꾸면 응답이 깨지거나 빈 값(`b''`)이 돌아옵니다 — 실제 baud 불일치와 똑같은 증상입니다.

## 실행/검증해 보기

```powershell
cd lecture/03_network/04_rs232
python src/serial_comm/main.py
```

예상 출력:
```
=== RS-232 패킷 프레이밍 데모 (하드웨어 불필요) ===
[1] format 모드 (TCP/IP와 동일)
    값 [123, 456]  -> 인코딩 "{123,456}"  -> 디코딩 [123, 456]  OK
    값 [90000, -45100, 30]  -> "{90000,-45100,30}"  -> [90000, -45100, 30]  OK
[2] non-format 모드 (ASCII decimal)
    문자열 "AB"  -> 코드 [65, 66]  -> 복원 "AB"  OK
------------------------------
패킷 프레이밍 왕복 검증 통과 ✅
```

✅ **체크포인트**: 마지막 줄이 `패킷 프레이밍 왕복 검증 통과 ✅`이고 종료 코드가 0이면 패킷 포맷 encode/decode가 정확히 왕복된 것입니다.

## 자주 하는 실수

### Q. `SerialException: could not open port 'COM6'`
A. com0com 쌍이 안 만들어졌거나 포트 번호 오타, 또는 다른 프로그램이 포트를 선점한 경우입니다. 장치 관리자에서 COM5/COM6을 확인하고(체크포인트), 다른 시리얼 프로그램을 종료하세요.

### Q. 응답이 `b''`(빈 값)로 옵니다.
A. 에코 서버가 안 떴거나 **baud 불일치**입니다. 에코 서버(COM6)를 먼저 띄우고, 양쪽 `--baud`를 동일(9600)하게 맞추세요.

### Q. 글자가 깨져서 옵니다.
A. **baud rate 불일치**(또는 데이터비트·패리티 불일치)입니다. 양측 baud를 동일하게 하고 기본 8N1을 유지하세요. RS-232는 자동 협상이 없어 수동으로 맞춰야 합니다.

### Q. 같은 포트를 두 번 열어 `PermissionError`가 납니다.
A. 한 포트(COM6)는 에코 서버만, 반대 포트(COM5)는 클라이언트만 열어야 합니다. 같은 포트를 두 프로그램이 동시에 열 수 없습니다.

### Q. HRSS 통신 화면에 아무것도 안 보입니다.
A. RS-232 설정에서 **"Show message"** 가 미체크된 경우입니다. 체크 후 테스트하세요(기본값은 미표시).

## 정리
- RS-232는 **1:1 점대점** 직렬 통신이며, 배선의 핵심은 **TX↔RX 교차 + 공통 GND**, 그리고 **양측 baud rate 동일**입니다.
- 명령어 흐름(`COPEN → CWRITE → CREAD`)과 패킷 포맷(`{ }`, `,`, non-format)은 **TCP/IP와 동일**하고, **`COPEN`의 첫 인자만 `ETH`→`SER`** 로 바뀝니다.
- 패킷 프레이밍 encode/decode를 포트 없이 검증했고, com0com으로 실제 시리얼 송수신까지 PC에서 재현할 수 있습니다.

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[05. MODBUS 기초](../../04_modbus/05_modbus_basics/README.md) — 점대점 통신을 넘어, 여러 장치를 **레지스터 단위**로 다루는 산업 표준 프로토콜로 넘어갑니다.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication User Manual* (C25UE801-2211)
  - **Ch.4 RS-232 Serial Communication** — p.34~36 (배선·교차 결선, baud rate 설정, HRSS/Caterpillar 경로, 패킷 포맷)
  - Ch.3 TCP/IP — `COPEN` 첫 인자: TCP/IP=`ETH`, RS-232=`SER`
- 실습 코드: [`_shared/serial_echo.py`](../../_shared/serial_echo.py), [`_shared/serial_client.py`](../../_shared/serial_client.py) (com0com 가상 COM 실습용)
