# HIWIN 산업용 로봇 통신 (Robot Communication) — 실습 트랙

> HIWIN 로봇 통신 매뉴얼(`docs/Robot_Communication_Manual-(E).pdf`, C25UE801-2211) 기반
> **실습 중심 / 시뮬레이터·소프트웨어 위주** 9편 강의 트랙. 실제 로봇 없이 **PC 한 대**로 전 과정을 따라할 수 있습니다.

- **대상**: 로봇·PLC·비전·그리퍼를 통신으로 연동해야 하는 자동화 엔지니어 (프로그래밍 기초 보유, 산업 통신/Modbus는 처음)
- **언어/도구**: Python 3.10+ / pymodbus 3.6.9 / pyserial 3.5 (실장비 측은 HRSS·Caterpillar)
- **검증 방식(혼합)**: PC 실습은 `python main.py` 자동 실행, 실장비 측은 HRSS/Caterpillar GUI·Modbus Monitor 관찰

---

## 트랙 매트릭스 (9편)

| # | path | project | 제목 | level | 선행 | 매뉴얼 |
|---|------|---------|------|-------|------|--------|
| 1 | [01_intro/01_setup](01_intro/01_setup/README.md) | `setup_check` | 실습 환경 준비 | 초급 | 없음 | – |
| 2 | [02_io/02_io](02_io/02_io/README.md) | `io_handshake` | I/O 통신 | 초급 | 01 | Ch.2 |
| 3 | [03_network/03_tcpip](03_network/03_tcpip/README.md) | `tcp_vision` | Ethernet TCP/IP | 초급 | 01 | Ch.3 |
| 4 | [03_network/04_rs232](03_network/04_rs232/README.md) | `serial_comm` | RS-232 직렬 통신 | 초급 | 03 | Ch.4 |
| 5 | [04_modbus/05_modbus_basics](04_modbus/05_modbus_basics/README.md) | `modbus_basics` | MODBUS 기초 | 중급 | 01 | Ch.5.1–5.2 |
| 6 | [05_server/06_modbus_server](05_server/06_modbus_server/README.md) | `server_motion` | MODBUS SERVER (로봇=슬레이브) | 중급 | 05 | Ch.5.3 |
| 7 | [06_client/07_modbus_client](06_client/07_modbus_client/README.md) | `client_gripper` | MODBUS CLIENT (로봇=마스터) | 중급 | 05 | Ch.5.4 |
| 8 | [07_debug/08_monitoring](07_debug/08_monitoring/README.md) | `modbus_monitor` | 모니터링 & 디버깅 | 중급 | 06,07 | Ch.5.5 |
| 9 | [08_capstone/09_cell](08_capstone/09_cell/README.md) | `cell_controller` | 종합 실습 — 자동화 셀 | 고급 | 전체 | 전 범위 |

부록: [A 치트시트](appendix/cheatsheet.md) · [B 32bit·IEEE754 변환](appendix/word-conversion.md) · [C 확인 문제 해답](appendix/solutions.md)

---

## 폴더 구조

```
lecture/
├── README.md                      이 파일 (트랙 인덱스)
├── _shared/                       모든 편이 공유하는 시뮬레이터·도구 (한 곳에서 관리)
│   ├── requirements.txt
│   ├── word_tools.py              32bit/IEEE754 변환
│   ├── modbus_master.py           Modbus 마스터 CLI + RobotMaster 클래스
│   ├── robot_server_sim.py        로봇 = Modbus 슬레이브
│   ├── gripper_sim.py             XEG 그리퍼 = Modbus 슬레이브
│   ├── tcp_echo_server.py         비전(TCP) 시뮬레이터
│   └── serial_echo.py / serial_client.py
├── 01_intro/01_setup/
│   ├── README.md                  강의 본문
│   ├── src/setup_check/main.py    실행/검증 단위
│   └── homework/
│       ├── README.md              과제 문제지
│       └── answer/homework_01/main.py ...
├── 02_io/02_io/ ...
└── appendix/
```

- **대형 시뮬레이터는 `_shared/`에 한 번만** 둡니다. 각 편의 `main.py`는 이를 import 하거나, 별도 터미널에서 standalone 으로 실행해 TCP로 접속합니다.
- 각 편의 `main.py` 상단 부트스트랩(공유 모듈 경로 추가):
  ```python
  import os, sys
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "_shared"))
  from word_tools import split_word          # 예
  from modbus_master import RobotMaster
  ```

---

## 시작하기

```powershell
# 1) 의존성 설치 (최초 1회)
cd lecture/_shared
python -m pip install -r requirements.txt
set PYTHONUTF8=1                       # 콘솔 한글 깨짐 방지

# 2) 1편부터 진행
cd ../01_intro/01_setup
python src/setup_check/main.py
```

각 편 README의 **실행/검증해 보기** 절에 예상 출력이 있습니다. 그대로 나오면 통과입니다.

## 실습 포트

| 역할 | 시뮬레이터 | 실습 포트 | 실제 장비 |
|------|-----------|-----------|-----------|
| 로봇(슬레이브) | `robot_server_sim.py` | 1502 | 502 |
| 그리퍼(슬레이브) | `gripper_sim.py` | 1503 | 502/RTU |
| 비전(TCP) | `tcp_echo_server.py` | 6000 | 임의 |

> 실제 장비는 502를 쓰지만, Windows 특권 포트 문제를 피하려 실습은 1502/1503을 사용합니다.

## 참고

- 원문 매뉴얼: [docs/Robot_Communication_Manual-(E).pdf](<../docs/Robot_Communication_Manual-(E).pdf>)
- 공유 도구 설명: [_shared/README.md](_shared/README.md)
