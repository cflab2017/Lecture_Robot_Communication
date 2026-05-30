# 부록 A. 명령어 & 레지스터 치트시트

> 한 화면에서 찾는 HIWIN 로봇 통신 핵심 표. 자세한 실습은 각 챕터 참조.

---

## 1. I/O 신호 & 명령 (→ [02편](../02_io/02_io/README.md))

| 종류 | 의미 | 채널수(6축 기준) | 입력 명령 | 출력 명령 |
|------|------|------------------|-----------|-----------|
| DI/O | Digital I/O (외부 배선) | 다수 | `DIN[n]` | `DO[n]` |
| SI/O | System I/O (제어 신호) | 시스템 정의 | `SI[n]` | `SO[n]` |
| FI/O | Flag(가상) I/O | 매핑 가능 | `FI[n]` | `FO[n]` |
| RI/O | Robot I/O (축/엔드) | 6 | `RI[n]` | `RO[n]` |
| MI/O | Modbus I/O (통신) | 맵 정의 | `MI[n]` | `MO[n]` |

**FI/O 기본 매핑**

| 입력(SI) | 신호 | 출력(SO) | 신호 |
|----------|------|----------|------|
| SI1 | Start | SO1 | Run |
| SI2 | Hold | SO2 | Held |
| SI3 | Stop | SO3 | Fault |
| SI4 | Enable | SO4 | Ready |
| SI5~8 | RSR1~4 | SO5~8 | ACK1~4 |

---

## 2. 시리얼 / 네트워크 통신 (→ [03편](../03_network/03_tcpip/README.md), [04편](../03_network/04_rs232/README.md))

| 명령 | 용도 |
|------|------|
| `COPEN(ETH, HANDLE)` | TCP/IP 연결 열기 |
| `COPEN(SER, HANDLE)` | RS-232 연결 열기 |
| `CWRITE(HANDLE, ...)` | 패킷 송신 |
| `CREAD(HANDLE, ...)` | 패킷 수신 |
| `CCLEAR(HANDLE)` | 버퍼/연결 정리 |

> 패킷은 `{ }`로 감싸고 항목은 콤마(`,`)로 구분. 예: `{1,100,200,0}`

---

## 3. MODBUS 기본 (→ [05편](../04_modbus/05_modbus_basics/README.md))

**표 A. 레지스터 4종**

| 종류 | 단위 | 접근 | 주소 범위(논리) |
|------|------|------|------------------|
| Discrete Input | 비트 | R | 10001~ |
| Coil | 비트 | R/W | 00001~ |
| Input Register | 16bit 워드 | R | 30001~ |
| Holding Register | 16bit 워드 | R/W | 40001~ |

**표 B. Function Code**

| FC | 동작 | FC | 동작 |
|----|------|----|------|
| 01 | Read Coils | 06 | Write Single Holding |
| 02 | Read Discrete Inputs | 15 | Write Multiple Coils |
| 03 | Read Holding Registers | 16 | Write Multiple Holding |
| 04 | Read Input Registers | 05 | Write Single Coil |

**표 C. RTU vs TCP**

| 구분 | 물리계층 | 에러 검증 |
|------|----------|-----------|
| RTU | RS-232/485 시리얼 | CRC-16 |
| TCP | Ethernet (포트 502) | TCP/IP 체크섬 + MBAP 헤더 |

---

## 4. MODBUS SERVER — 로봇 = 슬레이브 (→ [06편](../05_server/06_modbus_server/README.md))

**표 A. 시뮬레이터 레지스터 맵** (`robot_server_sim.py`, `zero_mode` → 주소 0-base)

| 영역 | 주소 | 내용 |
|------|------|------|
| Discrete Input (R) | 0~ | SO1.. (SO1=Run, SO2=Held, SO3=Fault, SO4=Ready) |
| Coil (R/W) | 0~ | SI1.. (SI1=Start, SI2=Hold, SI3=Stop, SI4=Enable) |
| Coil (R/W) | 300~ | DO1.. |
| Input Reg (R) | 100 | 속도 % |
| Input Reg (R) | 200 | 명령 상태 (1=Success) |
| Input Reg (R) | 201 | 현재 명령 번호 |
| Input Reg (R) | 300~311 | 관절 6축 L/H |
| Input Reg (R) | 400~411 | 직교 6축 L/H |
| Input Reg (R) | 524 | 동작 상태 (1 Idle / 2 Run / 3 Hold) |
| Holding Reg (R/W) | 100 | 속도 설정 |
| Holding Reg (R/W) | 200 | 실행 트리거 |
| Holding Reg (R/W) | 201 | 명령 번호 |
| Holding Reg (R/W) | 202 | 모션 타입 |
| Holding Reg (R/W) | 203~214 | 6축 좌표 L/H |
| Holding Reg (R/W) | 215 | 속도 |
| Holding Reg (R/W) | 216 | 가속 |
| Holding Reg (R/W) | 217 | Tool |
| Holding Reg (R/W) | 218 | Base |

**표 B. 단일 명령 번호** (HR201에 기록)

| No. | 명령 | No. | 명령 |
|-----|------|-----|------|
| 000 | PTP | 100 | Set PR |
| 001 | LIN | 101 | Set Tool |
| 002 | CIRC | 102 | Set Base |
| 003 | JOG | 103 | Set Current Tool |
| 004 | GO HOME | 104 | Set Current Base |
| 005 | T_STOP | 105 | Set Home |
| 006 | STOP | 200 | Get PR |
| | | 201 | Get Tool |
| | | 202 | Get Base |
| | | 203 | Get Current Tool |
| | | 204 | Get Current Base |
| | | 205 | Get Home |

**표 C. 명령 사이클**

```
HR201 (명령 번호 기록)
  → HR202~ (파라미터 기록)
  → HR200 = 1 (실행 트리거 ON)
  → IR200 == 1 확인 (완료/성공)
  → HR200 = 0 (트리거 해제)
```

---

## 5. MODBUS CLIENT — 로봇 = 마스터 (→ [07편](../06_client/07_modbus_client/README.md))

**표 A. MBC_* 명령**

| 명령 | 용도 | 주요 인자 |
|------|------|-----------|
| `MBC_RTU_OPEN` | RTU Client 열기 | 연결수, 국번, 통신속도, 패리티, 데이터비트, 정지비트, 시리얼포트 |
| `MBC_RTU_CLOSE` | RTU Client 닫기 | (없음) |
| `MBC_TCP_OPEN` | TCP Client 열기 | 연결번호, IP, 포트 |
| `MBC_TCP_CLOSE` | TCP Client 닫기 | 연결번호 |
| `MBC_READ_DINPUT` | Discrete Input 읽기 | 연결번호, 시작주소, 데이터, 길이 |
| `MBC_READ_COIL` | Coil 읽기 | 연결번호, 시작주소, 데이터, 길이 |
| `MBC_WRITE_COIL` | Coil 쓰기 | 연결번호, 시작주소, 데이터, 길이 |
| `MBC_READ_INPUT` | Input Reg 읽기 | 연결번호, 시작주소, 데이터, 타입(W/D), 길이 |
| `MBC_READ_HOLDING` | Holding Reg 읽기 | 연결번호, 시작주소, 데이터, 타입(W/D), 길이 |
| `MBC_WRITE_HOLDING` | Holding Reg 쓰기 | 연결번호, 시작주소, 데이터, 타입(W/D), 길이 |

> 타입: `W`=16bit 워드, `D`=32bit 더블워드. 레지스터 길이는 장비 허용 범위 내에서 지정.

**표 B. 데이터 처리 함수**

| 함수 | 용도 |
|------|------|
| `SWAP_WORD` | High/Low 워드 교환 |
| `IEEE754_ENCODE` | 실수 → IEEE754 정수 |
| `IEEE754_DECODE` | IEEE754 정수 → 실수 |

**표 C. HRSS MBC_* ↔ RobotMaster 메서드 대응** (`modbus_master.py`)

| HRSS 명령 | RobotMaster 메서드 |
|-----------|---------------------|
| `MBC_TCP_OPEN` | `open_tcp()` |
| `MBC_TCP_CLOSE` | `close_tcp()` |
| `MBC_READ_DINPUT` | `read_dinput()` |
| `MBC_READ_COIL` / `MBC_WRITE_COIL` | `read_coil()` / `write_coil()` |
| `MBC_READ_INPUT` | `read_input()` |
| `MBC_READ_HOLDING` / `MBC_WRITE_HOLDING` | `read_holding()` / `write_holding()` |

---

## 6. 실습 포트 & 도구 (→ [01편](../01_intro/01_setup/README.md), [_shared/](../_shared/README.md))

| 역할 | 시뮬레이터 파일 | 실습 포트 | 실제 장비 포트 |
|------|------------------|-----------|-----------------|
| 로봇 서버 | `robot_server_sim.py` | 1502 | 502 |
| 그리퍼 | `gripper_sim.py` | 1503 | 502 / RTU |
| 비전(TCP) | `tcp_echo_server.py` | 6000 | 임의 |
| 마스터 | `modbus_master.py` | - | - |
| 변환 | `word_tools.py` | - | - |
| 통합 | `cell_controller.py` (09편) | - | - |

---

## 7. 32bit / IEEE754 변환 한 줄 (→ [부록 B](word-conversion.md))

| 호출 | 결과 |
|------|------|
| `split_word(90000)` | `(24464, 1)` |
| `combine_word(24464, 1)` | `90000` |
| `swap_word(10)` | `655360` |
| `ieee754_encode(10.5)` | `1093140480` |

> 32bit 값은 Low/High 두 워드로 분리해 전송하고, 실수는 IEEE754 정수로 인코딩해 레지스터에 기록한다.
