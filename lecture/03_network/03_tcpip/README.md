# 03. Ethernet TCP/IP

로봇과 비전(상위) 시스템을 LAN 케이블 하나로 연결하고, 로봇이 "촬영해줘"(`{TRIG}`)라고 보내면 비전이 "여기 좌표"(`{X,Y,R}`)라고 답하는 흐름을 직접 만들어 봅니다. 실장비 HRSS의 `COPEN`/`CWRITE`/`CREAD`/`CCLEAR` 명령이 PC의 표준 `socket` 코드와 1:1로 대응된다는 점을 손으로 확인하는 것이 핵심입니다.

## 학습 목표
- TCP/IP가 성립하는 **동일 IP 도메인** 조건(앞 3옥텟 일치)을 설명하고 로봇/비전 IP를 맞춘다.
- `COPEN(ETH,HANDLE)`/`CWRITE`/`CREAD`/`CCLEAR` 4개 명령의 송수신 흐름을 작성한다.
- HRSS 패킷 규약(`{ }` 자동 감쌈, `,` 구분자)을 이해하고 패킷을 해석한다.
- PC에서 표준 `socket` 클라이언트(`로봇 Client`)를 작성해 비전 서버와 실제로 통신한다.

## 대상 환경
- 도구: Python 3.10+ (표준 `socket` 모듈만 사용 — 추가 설치 불필요)
- 플랫폼: Windows PC (시뮬레이션) — 검증된 비전 서버 [`_shared/tcp_echo_server.py`](../../_shared/tcp_echo_server.py)로 실장비 대체
- 검증: 터미널 A에 서버, 터미널 B에 `python src/tcp_vision/main.py`

## 핵심 개념

### 1) `COPEN` / `CWRITE` / `CREAD` / `CCLEAR` — 첫 인자가 ETH면 TCP/IP
HRSS에서 통신은 아래 4개 명령으로 끝납니다. **`COPEN`의 첫 인자가 `ETH`이면 TCP/IP, `SER`이면 RS-232**입니다. 한 글자 차이로 채널 종류가 완전히 달라집니다. (`SER`은 [04. RS-232](../../03_network/04_rs232/README.md)에서 다룹니다.)

| 명령 | 형식 | 역할 |
|------|------|------|
| `COPEN` | `COPEN(ETH, HANDLE)` | 채널을 연다. 첫 인자 **`ETH`=TCP/IP**, **`SER`=RS-232**. `HANDLE`은 이후 명령의 채널 식별자 |
| `CWRITE` | `CWRITE(HANDLE, SendData1, SendData2)` | 채널로 데이터를 **송신** (PC의 `sendall`) |
| `CREAD` | `CREAD(HANDLE, receiveData1, receiveData2)` | 채널에서 데이터를 **수신** (PC의 `recv`) |
| `CCLEAR` | `CCLEAR(HANDLE)` | 채널 버퍼를 **클리어**(이전 잔여 데이터 제거) |

> ⚠️ TCP는 `COPEN(ETH, ...)`, 시리얼은 `COPEN(SER, ...)`. 이번 편은 전부 `ETH`입니다.

### 2) TCP/IP는 "같은 동네"여야 통한다 — 동일 IP 도메인
데이터는 **같은 IP 네트워크 도메인**에서만 오갑니다. 즉 IP 주소의 **앞 3옥텟이 일치**해야 합니다.

| 장치 | IP 예시 | 통신 가능? |
|------|---------|-----------|
| 로봇 | `192.168.1.10` | — |
| 비전(상위) | `192.168.1.20` | ✅ 앞 3옥텟 `192.168.1` 일치 |
| 비전(상위) | `192.168.`**`2`**`.20` | ❌ 세 번째 옥텟이 다름 |

연결은 Ethernet 케이블로 **직렬 연결**하고, 상위 시스템이 여러 대면 **HUB**로 묶습니다. 카메라가 있으면 **PoE(Power over Ethernet)**로 LAN 케이블을 통해 전원을 함께 공급합니다.

### 3) 패킷 포맷 규약 — `{data}`와 콤마
| 규약 | 내용 | 예시 |
|------|------|------|
| 자동 감쌈 | 패킷 시작/끝에 중괄호 `{ }`가 자동으로 붙음 | `TRIG` 송신 → 실제 전송 `{TRIG}` |
| 구분자 | 값은 콤마 `,`로 구분 | `123.45,67.89,30.0` |
| non-format | 포맷을 끄면 시작/끝/구분 기호 없이 ASCII 10진수 1바이트씩 해석 | `A` → `65` |

> 상위 시스템은 항상 `{data}` 형태로 받습니다. 우리 PC 서버도 이 규약을 그대로 따릅니다. 테스트 전 네트워크 설정에서 **"Show message" 옵션을 체크**해야 통신 내용이 대화창에 보입니다(기본값은 꺼짐).

### 4) 누가 Client이고 누가 Server인가
| 역할 | 장치 | 동작 |
|------|------|------|
| **Client** | 🤖 로봇 | 먼저 접속(`COPEN`)하고 요청을 보냄 |
| **Server** | 💻 비전(상위) 시스템 | 포트를 열고 기다리다 응답을 줌 |

> 실습에서는 비전 서버를 PC(`tcp_echo_server.py`)가 대신하고, 우리는 **로봇 Client**를 Python으로 작성합니다.

## 예제로 보기

### 예제 — `src/tcp_vision/main.py` : 로봇 Client (비전 클라이언트)
비전 서버에 `{TRIG}`를 송신하고 `{X,Y,R}`을 수신·파싱합니다. (전체 코드는 파일 참조)

```python
# 핵심부 — COPEN(ETH) → CWRITE → CREAD 흐름
def send_packet(sock, payload):
    sock.sendall(("{" + payload + "}").encode("ascii"))   # CWRITE(HANDLE, payload)

def recv_packet(sock):
    data = sock.recv(1024).decode("ascii")                # CREAD(HANDLE, ...)
    return data.strip().strip("{}").split(",")            # { } 제거 후 , 로 파싱

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((args.host, args.port))                     # COPEN(ETH, HANDLE)
    send_packet(s, "TRIG")
    x, y, r = recv_packet(s)
    print(f"파싱 결과 -> X={x}, Y={y}, 회전각={r}")
# with 블록을 벗어나면 소켓이 닫힘 (CCLEAR + 채널 종료 역할)
```

🤖 방금 작성한 Python 흐름은 실장비 HRSS 코드와 **1:1로 대응**됩니다.

| 단계 | 💻 PC (Python) | 🤖 실장비 (HRSS) |
|------|----------------|------------------|
| 채널 열기 | `s.connect((host, port))` | `COPEN(ETH, HANDLE)` |
| 촬영 요청 송신 | `s.sendall("{TRIG}")` | `CWRITE(HANDLE, "TRIG")` |
| 좌표 수신 | `s.recv(1024)` | `CREAD(HANDLE, recv1, recv2)` |
| 버퍼 정리 | (with 블록 종료) | `CCLEAR(HANDLE)` |

> `{ }` 감쌈과 `,` 구분은 HRSS가 자동 처리하므로, 실장비에서는 payload(`TRIG`, 좌표값)만 신경 쓰면 됩니다.

## 실행/검증해 보기

**터미널 A** — 검증된 비전 서버를 띄웁니다.
```powershell
cd lecture/03_network/03_tcpip
python ../../_shared/tcp_echo_server.py --mode vision --port 6000
```
`vision` 모드의 동작(고정 시뮬레이션):

| 로봇이 보냄 | 서버가 응답 | 의미 (X, Y, 회전각) |
|-------------|-------------|---------------------|
| `{TRIG}` | `{123.45,67.89,30.0}` | 1번 부품 좌표 |
| `{TRIG2}` | `{-45.10,210.00,-15.0}` | 2번 부품 좌표 |
| 그 외 | `{0.00,0.00,0.0}` | 검출 없음 |

**터미널 B** — 로봇 Client를 실행합니다. (터미널 A는 그대로 둡니다)
```powershell
cd lecture/03_network/03_tcpip
python src/tcp_vision/main.py
```
예상 출력 (터미널 B):
```
=== TCP 비전 클라이언트 === 127.0.0.1:6000
송신: {TRIG}
수신: {123.45,67.89,30.0}
파싱 결과 -> X=123.45, Y=67.89, 회전각=30.0
```
이때 터미널 A(서버)에는 다음이 찍힙니다.
```
[연결] ('127.0.0.1', xxxxx) 접속
  수신: {TRIG}
  송신: {123.45,67.89,30.0}
```

✅ **체크포인트**: 터미널 B에 `X=123.45, Y=67.89, 회전각=30.0`이 출력되면 송신(`{TRIG}`) → 수신 → 파싱 전 과정이 성공한 것입니다.

## 자주 하는 실수

### Q. `ConnectionRefusedError`가 납니다.
A. 서버(터미널 A)가 안 떴거나 포트가 다릅니다. 서버를 먼저 띄우고, 서버와 클라이언트의 `--port`를 동일하게(6000) 맞추세요.

### Q. 🤖 실장비에서 통신 자체가 안 됩니다.
A. IP **앞 3옥텟이 불일치**하는 경우가 가장 흔합니다. 로봇·비전 IP의 세 번째 옥텟까지 동일한지 확인하세요(예: 둘 다 `192.168.1.xx`). 또한 `COPEN`의 첫 인자가 `ETH`인지(시리얼은 `SER`) 확인합니다.

### Q. 응답이 안 오고 멈춥니다.
A. 패킷 끝 기호 `}`가 빠진 경우입니다. 서버는 `}` 단위로 패킷을 처리하므로, 송신 문자열을 반드시 `{ ... }`로 감쌌는지 확인하세요.

### Q. 좌표가 항상 `0.00,0.00,0.0`으로 옵니다.
A. 서버가 모르는 요청을 받은 것입니다. payload를 정확히 `TRIG` 또는 `TRIG2`로 보내세요. (값이 깨져 보이면 "Show message" 미체크 또는 non-format 상태인지 점검)

## 정리
- TCP/IP 성립 조건(동일 IP 도메인, 앞 3옥텟 일치)과 연결 구조(HUB, PoE)를 이해했습니다.
- `COPEN(ETH,…)`/`CWRITE`/`CREAD`/`CCLEAR` 4개 명령과 `{ }`·`,` 패킷 규약을 익혔습니다.
- PC에서 비전 서버를 띄우고, 직접 작성한 `로봇 Client`로 실제 송수신·파싱에 성공했습니다.
- PC 코드 ↔ HRSS 코드 1:1 대응으로 실장비 프로그램의 뼈대를 확보했습니다.

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[04. RS-232](../../03_network/04_rs232/README.md) — 같은 송수신 논리를 케이블(시리얼) 위에서 구현합니다. `COPEN`의 첫 인자가 `ETH`에서 `SER`로 바뀌는 것에 주목하세요.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication User Manual* (C25UE801-2211)
  - **Ch.3 Ethernet TCP/IP communication method** (p.30~33)
  - 동일 IP 도메인 / HUB / PoE, IP 설정 경로, 패킷 포맷(`{ }`·`,`·Show message), `COPEN`/`CWRITE`/`CREAD`/`CCLEAR` 및 Client(Robot)–Server(Vision) 구조
- 실습 코드: [`_shared/tcp_echo_server.py`](../../_shared/tcp_echo_server.py) (동작 검증됨)
