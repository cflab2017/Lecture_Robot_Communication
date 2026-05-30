# 02. I/O 통신

I/O 통신은 **전선 한 가닥을 ON/OFF** 시켜 로봇과 상대 장비(PLC·머신·센서)가 신호를 주고받는 가장 기본적인 통신입니다. 로봇이 출력(`$DO`)을 켜면 상대가 입력으로 읽고, 상대가 응답을 켜면 로봇이 입력(`$DI`)으로 읽습니다. 이 **주고받기(핸드셰이크)** 가 모든 자동화의 기초 패턴입니다.

이 편에서는 HIWIN 로봇의 I/O 5종을 정리하고, 픽앤플레이스 한 사이클의 그립/언그립 핸드셰이크를 **순수 Python 상태기계**로 재현합니다. 물리 배선·시뮬레이터·시리얼 포트 없이 PC 한 대로 로직을 손에 익힙니다.

## 학습 목표
- HIWIN 로봇의 **I/O 5종**(DI/O·SI/O·FI/O·RI/O·MI/O)을 구분하고 채널 수·변수를 안다.
- `$DO[n]=TRUE` 출력과 `WAIT FOR $DI[n]==TRUE` 대기로 핸드셰이크를 설계한다.
- FI/O 기본 매핑(Start/Hold/Stop/Enable/RSR, Run/Held/Fault/Ready/ACK)을 읽는다.
- 픽앤플레이스 두 핸드셰이크(그립 `$DI[1]`, 언그립 `$DI[4]`)를 Python 상태기계로 재현해 실행한다.

## 대상 환경
- 도구: Python 3.10+ (표준 라이브러리만 사용 — 추가 설치 불필요)
- 플랫폼: Windows PC (시뮬레이션) — 실제 로봇/PLC/그리퍼·포트 불필요
- 검증: CLI 자동실행 — `python src/io_handshake/main.py`

## 핵심 개념

I/O 통신 = "전선 한 가닥 = 신호 1개". 로봇이 출력(`$DO`)을 ON 하면 상대가 입력으로 읽고, 상대가 응답을 ON 하면 로봇이 입력(`$DI`)으로 읽습니다. 이 핸드셰이크가 핵심입니다.

### 1) I/O 5종 한눈에 보기

| 종류 | 풀네임 | 채널(6축 기준) | 변수 | 비고 |
|------|--------|----------------|------|------|
| **DI/O** | Digital I/O | 24 I / 24 O | `$DI` / `$DO` | PLC·머신·센서와 일반 디지털 신호 (SCARA는 16I/8O) |
| **SI/O** | Fieldbus I/O | 128 I / 128 O | `$SI` / `$SO` | CC-Link / Profinet / EtherNet/IP **옵션 카드** 필요 |
| **FI/O** | Functional I/O | 8 I / 8 O | (기능 고정) | Start·Hold·Stop·Enable·RSR 등 **기능 신호** |
| **RI/O** | Robot I/O | 6 I / 4 O | `$RI` / `$RO` | 로봇 본체 말단 배선. **SCARA·Delta 불가** |
| **MI/O** | Module I/O | 32 I / 32 O | `$MI` / `$MO` | 여러 I/O를 묶어 모듈로 감시 (시작/끝 I/O 지정) |

> ⚠️ **채널 수는 모델마다 다릅니다.** 위 숫자는 6축 관절로봇(RA605 등) 기준이며, 반드시 해당 로봇/컨트롤러 매뉴얼을 확인하세요. 일부 모델은 확장 I/O를 추가할 수 있습니다.

### 2) 입출력 명령

| 종류 | 입력(읽기) | 출력(쓰기) | 범위 |
|------|-----------|-----------|------|
| Digital | `WAIT FOR $DI[n]==TRUE` / `==FALSE` | `$DO[n]=TRUE` / `=FALSE` | n=1~24 |
| Fieldbus | `WAIT FOR $SI[n]==TRUE` / `==FALSE` | `$SO[n]=TRUE` / `=FALSE` | n=1~128 |
| Function | N/A (상위가 입력에 직결) | N/A (출력이 상위에 직결) | 1~8 |
| Robot | `WAIT FOR $RI[m]==TRUE` / `==FALSE` | `$RO[n]=TRUE` / `=FALSE` | m=1~6, n=1~4 |
| Module | `WAIT FOR $MI[n]==TRUE` / `==FALSE` | `$MO[n]=TRUE` / `=FALSE` | n=1~32 |

> `WAIT FOR` 는 조건이 참이 될 때까지 **그 줄에서 멈춰 기다리는** 블로킹 명령입니다. 핸드셰이크의 "응답 대기"가 바로 이것입니다.

### 3) FI/O 기본 매핑

기능 I/O는 핀 번호에 **고정된 기능**이 있습니다. (SI/O를 쓰는 경우 `$SI[1]~$SI[8]` / `$SO[1]~$SO[8]` 가 그 역할을 합니다.)

| 입력 $SI[n] | 기능 | 출력 $SO[n] | 기능 |
|-------------|------|-------------|------|
| $SI[1] | Start (시작) | $SO[1] | Run (운전중) |
| $SI[2] | Hold (일시정지) | $SO[2] | Held (정지됨) |
| $SI[3] | Stop (정지) | $SO[3] | Fault (이상) |
| $SI[4] | Enable (구동허가) | $SO[4] | Ready (준비완료) |
| $SI[5~8] | RSR1~4 (로봇 서비스 요청) | $SO[5~8] | ACK1~4 (요청 응답) |

### 4) CN6 포트 결선 (NPN) 개념

- 실제 디지털 I/O는 컨트롤러의 **CN6 포트**에서 단자대(terminal block)로 빠져나와 PLC·센서와 연결됩니다.
- 입력·출력 모두 **NPN(싱크) 방식**: 신호선이 `0V(GND)`로 떨어질 때 "ON"으로 인식합니다. (PNP 장비와 섞으면 동작하지 않으니 결선 방식을 반드시 맞추세요.)
- 결선 시 외부 24V 전원의 공통선(COM)과 GND를 정확히 물리는 것이 핵심이며, 잘못된 극성은 입력이 항상 ON/OFF로 고정되는 증상을 만듭니다.

## 예제로 보기

### 예제 — `src/io_handshake/main.py` : 픽앤플레이스 I/O 핸드셰이크 상태기계
물리 I/O는 PC로 직접 만들 수 없으므로, **로봇과 PLC가 신호를 주고받는 로직**을 순수 Python 상태기계로 재현합니다. 신호 상태는 딕셔너리로 흉내 냅니다. (전체 코드는 파일 참조)

```python
# 핵심부 — $DO 출력 → PLC 응답 → WAIT FOR $DI 한 번의 핸드셰이크
DO = {6: False}            # 로봇 출력: $DO[6] = 그리퍼 CLOSE/OPEN 지령
DI = {1: False, 4: False}  # 로봇 입력: $DI[1]=그립완료, $DI[4]=언그립완료

def handshake(title, do_pin, do_value, di_pin, note=""):
    robot_set_do(do_pin, do_value, note)   # $DO[n]=TRUE/FALSE
    plc_respond(do_pin, di_pin)            # 잠시 뒤 $DI[n]=TRUE 로 응답
    robot_wait_for(di_pin)                 # WAIT FOR $DI[n]==TRUE

handshake("GRIP",   do_pin=6, do_value=True,  di_pin=1)  # 집기 → $DI[1]
handshake("UNGRIP", do_pin=6, do_value=False, di_pin=4)  # 놓기 → $DI[4]
```

> 🤖 **실장비(HRSS)** — 위 두 핸드셰이크는 실제로는 다음 HRSS 픽앤플레이스 프로그램의 일부입니다. 워크피스를 한 곳에서 집어(PICK) 다른 곳에 놓는(PLACE) 한 사이클이며, `$DO[6]` 으로 그리퍼를 여닫고 `WAIT FOR $DI` 로 그립/언그립 완료를 기다립니다. (P1/P3은 P2/P4 위 +50mm 접근점으로, 워크피스에 **수직 접근**해 충돌·끌림을 막습니다.)

```
PTP P0 FINE=1 Vel=100% Acc=75% TOOL[0] BASE[0]      ; HOME에서 시작
PTP P1 FINE=1 Vel=100% Acc=75% TOOL[0] BASE[0]      ; PICK 위로 접근
LIN P2 FINE=1 Vel=100mm/s Acc=75% TOOL[0] BASE[0]   ; 수직 하강해 집는 점
$DO[6]=TRUE                                          ; 그리퍼 닫기(집기) 지령
WAIT FOR $DI[1]==TRUE                                ; 그립완료 응답 대기
LIN P1 FINE=1 Vel=100mm/s Acc=75% TOOL[0] BASE[0]   ; 수직 상승(워크 들고)
PTP P3 FINE=1 Vel=100% Acc=75% TOOL[0] BASE[0]      ; PLACE 위로 이동
LIN P4 FINE=1 Vel=100mm/s Acc=75% TOOL[0] BASE[0]   ; 수직 하강해 놓는 점
$DO[6]=FALSE                                         ; 그리퍼 열기(놓기) 지령
WAIT FOR $DI[4]==TRUE                                ; 언그립완료 응답 대기
LIN P3 FINE=1 Vel=100mm/s Acc=75% TOOL[0] BASE[0]   ; 수직 상승(빈 손)
PTP P0 FINE=1 Vel=100% Acc=75% TOOL[0] BASE[0]      ; HOME 복귀
```

> `PTP`(점대점)는 빠른 자유 이동, `LIN`(직선)은 워크피스 근처의 정밀한 수직 접근에 씁니다.

## 실행/검증해 보기

```powershell
cd lecture/02_io/02_io
$env:PYTHONUTF8=1        # 한글/이모지 출력 보장
python src/io_handshake/main.py
```

예상 출력:
```
픽앤플레이스 I/O 핸드셰이크 시뮬레이션 시작

== GRIP (집기): $DO[6] ON, $DI[1] 그립완료 대기 ==
   [ROBO] $DO[6]=TRUE 출력
   [PLC ] $DO[6]=ON 감지 → 액추에이터 동작 중...
   [PLC ] 동작 완료 → $DI[1]=TRUE 응답
   [ROBO] WAIT FOR $DI[1]==TRUE ...
   [ROBO] $DI[1]==TRUE 확인 → 다음 동작 진행

== UNGRIP (놓기): $DO[6] OFF, $DI[4] 언그립완료 대기 ==
   [ROBO] $DO[6]=FALSE 출력 (그리퍼 OPEN)
   [PLC ] $DO[6]=OFF 감지 → 액추에이터 동작 중...
   [PLC ] 동작 완료 → $DI[4]=TRUE 응답
   [ROBO] WAIT FOR $DI[4]==TRUE ...
   [ROBO] $DI[4]==TRUE 확인 → 다음 동작 진행

사이클 완료 ✅  (모든 핸드셰이크 정상 종료)
```

✅ **체크포인트**: `[ROBO] $DO ... 출력` → `[PLC] ... 응답` → `[ROBO] WAIT FOR ... 확인` 순서가 **두 번** 반복되고 마지막에 `사이클 완료 ✅` 가 보이면 성공입니다.

## 자주 하는 실수

### Q. `WAIT FOR` 에서 멈추지 않고 바로 통과해요.
A. 입력이 항상 ON으로 고정된 경우입니다(보통 NPN/PNP 결선 반대). CN6 결선을 NPN(싱크)로 맞추고 외부 24V의 COM/GND 극성을 확인하세요. 코드에서는 다음 핸드셰이크 전에 해당 `$DI` 비트를 `False` 로 초기화하지 않으면 같은 증상이 납니다.

### Q. `$DO` 를 ON 해도 상대가 반응이 없어요.
A. 출력 채널·번호 오타이거나 외부 24V 전원이 인가되지 않은 경우입니다. 채널 번호를 재확인하고 단자대 전원을 점검하세요.

### Q. `$RI`/`$RO` 또는 `$SI`/`$SO` 가 없다는 오류가 나요.
A. RI/O는 **SCARA·Delta 모델에서 미지원**이므로 DI/O 또는 MI/O로 대체합니다. SI/O는 **Fieldbus 옵션 카드**(CC-Link/Profinet/EtherNet/IP)가 장착돼야 동작합니다.

### Q. 콘솔에서 한글/✅ 가 깨져요.
A. Windows 콘솔 기본 인코딩(cp949) 문제입니다. `set PYTHONUTF8=1`(PowerShell은 `$env:PYTHONUTF8=1`) 후 실행하세요. (main.py도 `stdout.reconfigure(encoding="utf-8")` 로 한 번 더 방어합니다.)

## 정리
- I/O 5종(DI/O·SI/O·FI/O·RI/O·MI/O)의 채널 수·변수와 입출력 명령을 익혔습니다.
- `$DO` 출력 → 상대 응답 → `WAIT FOR $DI` 라는 **핸드셰이크**가 모든 자동화의 기본 패턴임을 픽앤플레이스로 확인했습니다.
- 물리 신호 1개로 통신하던 I/O를, 이후 Modbus 편에서는 **코일·레지스터 비트**로 소프트웨어끼리 실제로 교환하게 됩니다.

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[03. Ethernet TCP/IP](../../03_network/03_tcpip/README.md) — 신호 1개로 통신하던 I/O를, 문자열 메시지를 주고받는 TCP/IP 방식으로 확장합니다.

## 📖 매뉴얼 출처
- HIWIN *Robot Communication* User Manual, **Chapter 2 Input/Output (I/O) communication method** (p.20~29).
  - Table 1 (I/O 5종), Table 2 (입출력 코드), Step 1~4 픽앤플레이스 예제, Table 4·5 (DI/O·SI/O 핸드셰이크 표).
- PC 시뮬레이션 코드는 본 강의 자체 구성.
