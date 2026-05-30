# 01. 실습 환경 준비

이 트랙은 **실제 로봇 없이 PC 한 대**로 HIWIN 로봇 통신을 재현합니다. 첫 편에서는 도구를 설치하고, 공유 라이브러리(`_shared/`)를 불러오는 구조를 이해하며, 환경 자가진단 스크립트로 "준비 완료"를 확인합니다. 여기서 한 번만 제대로 맞춰 두면 이후 8편을 막힘 없이 진행할 수 있습니다.

## 학습 목표
- Python · pymodbus · pyserial을 설치하고 버전을 확인한다.
- 각 편의 `main.py`가 `_shared/` 공유 모듈을 불러오는 부트스트랩 구조를 이해한다.
- 실습 포트(로봇 1502 / 그리퍼 1503 / 비전 6000)와 502 포트 회피 이유를 설명한다.
- 환경 자가진단 스크립트를 실행해 "통과"를 확인한다.

## 대상 환경
- 도구: Python 3.10+ / pymodbus 3.6.9 / pyserial 3.5
- 플랫폼: Windows PC (시뮬레이션) — 실제 로봇/PLC/그리퍼 불필요
- 검증: CLI 자동실행 — `python src/setup_check/main.py`

## 핵심 개념

### 1) 무엇을 시뮬레이터로 대체하나
| 실제 장비 | 본 트랙의 대체 |
|-----------|----------------|
| 로봇(Modbus 슬레이브) | [`_shared/robot_server_sim.py`](../../_shared/robot_server_sim.py) |
| XEG 전동 그리퍼 | [`_shared/gripper_sim.py`](../../_shared/gripper_sim.py) |
| 상위 PLC/마스터 | [`_shared/modbus_master.py`](../../_shared/modbus_master.py) |
| 비전/상위 시스템(TCP) | [`_shared/tcp_echo_server.py`](../../_shared/tcp_echo_server.py) |
| RS-232 케이블 | com0com 가상 COM 포트 (04편) |

### 2) `_shared/` 공유 라이브러리
대형 시뮬레이터를 편마다 복제하지 않고 `lecture/_shared/`에 한 번만 둡니다. 각 편은 두 가지 방식으로 이를 씁니다.
- **standalone 실행**: 시뮬레이터는 별도 터미널에서 직접 띄우고, 편의 코드는 TCP로 접속합니다(import 안 함).
- **모듈 import**: `word_tools`, `modbus_master` 같은 헬퍼는 `main.py`가 import 합니다.

### 3) 깊이에 무관한 import 부트스트랩
편 파일은 `GROUP/LEC/src/PROJECT/main.py`처럼 깊이 들어가 있어, 상대 경로 대신 **상위로 올라가며 `_shared/`를 탐색**합니다.
```python
import os, sys
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "_shared")):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, "_shared"))
```

### 4) 실습 포트와 502 회피
| 역할 | 시뮬레이터 | 실습 포트 | 실제 |
|------|-----------|-----------|------|
| 로봇 | robot_server_sim.py | 1502 | 502 |
| 그리퍼 | gripper_sim.py | 1503 | 502 |
| 비전 | tcp_echo_server.py | 6000 | 임의 |

Windows에서 502 같은 1024 미만 포트는 관리자 권한이 필요할 수 있어 실습은 1502/1503을 씁니다.

## 환경 준비

```powershell
# 1) 의존성 설치 (최초 1회)
cd lecture/_shared
python -m pip install -r requirements.txt

# 2) 콘솔 한글 깨짐 방지 (매 세션)
set PYTHONUTF8=1           # PowerShell: $env:PYTHONUTF8=1
```

## 예제로 보기

### 예제 1 — `src/setup_check/main.py` : 환경 자가진단
Python 버전, 의존성, 공유 모듈 import + 변환값을 한 번에 점검합니다. (전체 코드는 파일 참조)

```python
# 핵심부 — _shared 탐색 후 word_tools 로 변환 검증
from word_tools import split_word, combine_word, ieee754_encode
a = split_word(90000)                 # -> (24464, 1)
assert combine_word(*a) == 90000
assert ieee754_encode(10.5) == 1093140480
print("환경 점검 통과 ✅")
```

## 실행/검증해 보기

```powershell
cd lecture/01_intro/01_setup
python src/setup_check/main.py
```

예상 출력 (Python 버전 숫자만 환경에 따라 다름):
```
=== 실습 환경 점검 ===
[1] Python 3.12.10  OK
[2] pymodbus 3.6.9 / pyserial 3.5  OK
[3] _shared import OK: split_word(90000)=(24464, 1), ieee754_encode(10.5)=1093140480
------------------------------
환경 점검 통과 ✅
```

✅ **체크포인트**: 마지막 줄이 `환경 점검 통과 ✅` 이고 종료 코드가 0이면 준비 완료입니다.

## 자주 하는 실수

### Q. `ModuleNotFoundError: No module named 'pymodbus'`
A. 의존성 미설치 또는 다른 Python에 설치된 경우입니다. `python -m pip install -r ../../_shared/requirements.txt`로 **현재 Python**에 설치하세요.

### Q. 한글이 `????`나 깨진 문자로 나와요.
A. Windows 콘솔 기본 인코딩(cp949) 문제입니다. `set PYTHONUTF8=1`(PowerShell은 `$env:PYTHONUTF8=1`) 후 실행하세요.

### Q. `from word_tools import ...` 에서 `ModuleNotFoundError`.
A. `_shared/` 탐색 부트스트랩이 빠졌거나, `_shared` 폴더 밖에서 파일을 옮긴 경우입니다. 부트스트랩 6줄이 `main.py` 최상단에 있는지 확인하세요.

### Q. 포트 502로 시뮬레이터가 안 떠요 (`Permission denied`).
A. 특권 포트입니다. `--port 1502`처럼 1024 이상을 쓰세요.

## 정리
- PC만으로 로봇/그리퍼/비전/마스터를 시뮬레이션할 준비를 마쳤습니다.
- 공유 코드는 `_shared/`에 모으고, 각 편은 부트스트랩으로 이를 불러옵니다.
- 실습 포트는 1502/1503/6000을 사용합니다.

## 직접 해 보기
[`homework/`](homework/README.md) 폴더의 과제를 풀어 보세요. 정답은 [`homework/answer/`](homework/answer/)에 있습니다.

## 다음 단원
[02. I/O 통신](../../02_io/02_io/README.md) — 가장 기본인 디지털 I/O 핸드셰이크로 로봇과 PLC가 신호를 주고받는 원리를 실습합니다.

## 📖 매뉴얼 출처
- 실습 환경은 본 트랙 자체 구성. 포트·레지스터 근거는 이후 각 편에서 표기.
