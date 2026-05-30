# 공유 라이브러리 (`_shared/`)

모든 편이 공유하는, PC만으로 HIWIN 로봇 통신을 재현하는 Python 도구·시뮬레이터입니다.
대형 시뮬레이터를 편마다 복제하지 않고 여기 한 곳에서 관리합니다. (pymodbus 3.6.9 / pyserial 3.5 기준, 전부 실행 검증 완료)

## 설치

```powershell
cd lecture/_shared
python -m pip install -r requirements.txt
# Windows 콘솔에서 한글이 깨지면:
set PYTHONUTF8=1     # PowerShell: $env:PYTHONUTF8=1
```

## 각 편에서 가져다 쓰는 법

- **standalone 시뮬레이터**(로봇/그리퍼/비전)는 별도 터미널에서 직접 실행하고, 편의 `main.py`는 TCP/소켓으로 접속합니다(import 불필요).
  ```powershell
  python lecture/_shared/robot_server_sim.py --port 1502 --host 127.0.0.1
  ```
- **헬퍼 모듈**(`word_tools`, `modbus_master`)은 편의 `main.py`가 import 합니다. 경로 부트스트랩:
  ```python
  import os, sys
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "_shared"))
  from word_tools import split_word
  from modbus_master import RobotMaster
  ```
  (편 파일 위치가 `GROUP/LEC/src/PROJECT/main.py` 이므로 `_shared` 까지 4단계 상위입니다.)

## 파일 목록

| 파일 | 역할 | 사용 편 |
|------|------|---------|
| [`word_tools.py`](word_tools.py) | 32bit Low/High word 분할·복원, SWAP_WORD, IEEE754 변환 | 05, 07, 부록 B |
| [`modbus_master.py`](modbus_master.py) | Modbus 마스터 CLI + `RobotMaster` 클래스 | 05, 06, 07 |
| [`robot_server_sim.py`](robot_server_sim.py) | 로봇 = Modbus 슬레이브 (명령 사이클 구현) | 06, 09 |
| [`gripper_sim.py`](gripper_sim.py) | XEG 전동 그리퍼 = Modbus 슬레이브 | 07, 09 |
| [`tcp_echo_server.py`](tcp_echo_server.py) | TCP/IP 상위 시스템(비전) 시뮬레이터, `{data}` 포맷 | 03, 09 |
| [`serial_echo.py`](serial_echo.py) | RS-232 시리얼 에코 서버(가상 COM) | 04 |
| [`serial_client.py`](serial_client.py) | RS-232 시리얼 클라이언트(가상 COM) | 04 |

> I/O 핸드셰이크(02편)와 통합 컨트롤러(09편)는 각 편의 `src/<project>/main.py`에 포함되어 있습니다.

## 빠른 동작 확인

```powershell
# 1) 변환 도구 (장비 불필요)
python word_tools.py

# 2) 로봇 서버 띄우기 (한 터미널)
python robot_server_sim.py --port 1502 --host 127.0.0.1

# 3) 다른 터미널에서 마스터로 제어
python modbus_master.py --port 1502 read-di 0 8     # SO1~SO8 (SO4=Ready)
python modbus_master.py --port 1502 read-ir 524 1   # 동작상태(1=Idle)
```

> **포트 502 권한**: Windows에서 502 포트는 관리자 권한이 필요할 수 있습니다. 실습에서는 `--port 1502` 처럼
> 1024 이상 포트를 쓰면 권한 문제 없이 진행됩니다. 실제 로봇/장비는 502를 사용합니다.

> **두 시뮬레이터 동시 실행**: 포트를 분리하세요. 예) 로봇 `--port 1502`, 그리퍼 `--port 1503`.
