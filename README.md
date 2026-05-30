# HIWIN 산업용 로봇 통신 실습 트랙 (Robot Communication)

HIWIN 산업용 로봇 통신 매뉴얼(`C25UE801-2211`)을 바탕으로 만든 **실습 중심 한국어 강의 트랙**입니다.
**실제 로봇·PLC·그리퍼가 없어도 PC 한 대**로 I/O · TCP/IP · RS-232 · **MODBUS(RTU/TCP)** 통신을 직접 돌려보며 익힙니다.

> 모든 실습 코드는 Python 시뮬레이터로 동작하며, 강의에 실린 예상 출력은 실제 실행으로 검증되었습니다.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![pymodbus](https://img.shields.io/badge/pymodbus-3.6.9-green)
![lectures](https://img.shields.io/badge/lectures-9%ED%8E%B8-orange)

---

## ✨ 특징

- **장비 불필요** — 로봇/그리퍼/비전/PLC를 Python 시뮬레이터로 대체, PC만으로 전 과정 실습
- **실습 중심** — 편마다 실행 가능한 `main.py` + 풀어보는 `homework`(정답 포함)
- **검증된 예제** — 모든 `main.py`·정답을 실제 실행해 예상 출력과 일치 확인
- **현장 매핑** — 시뮬레이터 포트(1502/1503/6000)와 실장비(HRSS/Caterpillar, 502) 대응 표기

## 🎯 대상

로봇·PLC·비전·그리퍼를 **통신으로 연동**해야 하는 자동화 엔지니어. 프로그래밍 기초는 있으나 산업 통신/Modbus는 처음인 분.

---

## 🚀 빠른 시작

```bash
# 1) 저장소 클론
git clone https://github.com/cflab2017/Lecture_Robot_Communication.git
cd Lecture_Robot_Communication

# 2) 의존성 설치 (pymodbus 3.6.9 / pyserial 3.5)
cd lecture/_shared
python -m pip install -r requirements.txt

# (Windows 콘솔 한글 깨짐 방지)
set PYTHONUTF8=1        # PowerShell: $env:PYTHONUTF8=1

# 3) 1편부터 시작 — 환경 자가진단
cd ../01_intro/01_setup
python src/setup_check/main.py
# → "환경 점검 통과 ✅" 가 보이면 준비 완료
```

전체 안내는 **[강의 트랙 인덱스](lecture/README.md)** 를 참고하세요.

---

## 📚 커리큘럼 (9편)

| # | 편 | 핵심 실습 | 매뉴얼 |
|---|-----|-----------|--------|
| 1 | [실습 환경 준비](lecture/01_intro/01_setup/README.md) | Python·pymodbus 설치, 공유 모듈 구조 이해 | – |
| 2 | [I/O 통신](lecture/02_io/02_io/README.md) | `$DI/$DO` 핸드셰이크 픽앤플레이스 | Ch.2 |
| 3 | [Ethernet TCP/IP](lecture/03_network/03_tcpip/README.md) | `COPEN/CWRITE/CREAD`로 비전과 `{data}` 송수신 | Ch.3 |
| 4 | [RS-232 직렬 통신](lecture/03_network/04_rs232/README.md) | 패킷 프레이밍 · 가상 COM 시리얼 | Ch.4 |
| 5 | [MODBUS 기초](lecture/04_modbus/05_modbus_basics/README.md) | 4종 레지스터·Function Code 직접 읽기/쓰기 | Ch.5.1–5.2 |
| 6 | [MODBUS SERVER (로봇=슬레이브)](lecture/05_server/06_modbus_server/README.md) | 마스터에서 명령 사이클로 로봇 PTP 이동 | Ch.5.3 |
| 7 | [MODBUS CLIENT (로봇=마스터)](lecture/06_client/07_modbus_client/README.md) | `MBC_*`로 그리퍼 제어, IEEE754 변환 | Ch.5.4 |
| 8 | [모니터링 & 디버깅](lecture/07_debug/08_monitoring/README.md) | Wireshark 패킷 캡처·손해독 | Ch.5.5 |
| 9 | [종합 실습 — 자동화 셀](lecture/08_capstone/09_cell/README.md) | 비전→로봇→그리퍼 통합 오케스트레이션 | 전 범위 |

**부록**: [A. 명령어 치트시트](lecture/appendix/cheatsheet.md) · [B. 32bit·IEEE754 변환 실습](lecture/appendix/word-conversion.md) · [C. 확인 문제 해답](lecture/appendix/solutions.md)

---

## 🗂️ 저장소 구조

```
Lecture_Robot_Communication/
├── README.md                     이 파일 (저장소 소개)
├── docs/
│   └── Robot_Communication_Manual-(E).pdf   원문 매뉴얼 (C25UE801-2211)
└── lecture/
    ├── README.md                 강의 트랙 인덱스 (9편 매트릭스·시작 가이드)
    ├── _shared/                  모든 편이 공유하는 시뮬레이터·도구
    │   ├── word_tools.py            32bit/IEEE754 변환
    │   ├── modbus_master.py         Modbus 마스터 CLI + RobotMaster 클래스
    │   ├── robot_server_sim.py      로봇 = Modbus 슬레이브
    │   ├── gripper_sim.py           XEG 그리퍼 = Modbus 슬레이브
    │   ├── tcp_echo_server.py       비전(TCP) 시뮬레이터
    │   └── serial_echo.py / serial_client.py
    ├── 01_intro/01_setup/        편마다 동일한 구조 ↓
    │   ├── README.md                강의 본문
    │   ├── src/<project>/main.py    실행·검증 단위
    │   └── homework/
    │       ├── README.md            과제 문제지
    │       └── answer/homework_NN/main.py
    ├── 02_io/ … 08_capstone/     (총 9편)
    └── appendix/                 치트시트 · 변환 실습 · 해답
```

- **공유 시뮬레이터는 `_shared/`에 한 번만** 둡니다. 각 편의 `main.py`는 상위로 올라가며 `_shared`를 탐색하는 부트스트랩으로 모듈을 불러오거나, 별도 터미널에서 standalone으로 띄워 TCP로 접속합니다.

---

## 🔌 실습 포트

| 역할 | 시뮬레이터 | 실습 포트 | 실제 장비 |
|------|-----------|-----------|-----------|
| 로봇(슬레이브) | `robot_server_sim.py` | 1502 | 502 |
| 그리퍼(슬레이브) | `gripper_sim.py` | 1503 | 502 / RTU |
| 비전(TCP) | `tcp_echo_server.py` | 6000 | 임의 |

> 실제 장비는 502를 쓰지만, Windows 특권 포트 문제를 피하려 실습은 1502/1503을 사용합니다.

## 🧰 요구 환경

- Python **3.10+**
- `pymodbus==3.6.9`, `pyserial==3.5` (`lecture/_shared/requirements.txt`)
- (선택) Wireshark + Npcap(8편), com0com 가상 COM(4편)

---

## 📖 출처 & 라이선스

- 원문 매뉴얼: [docs/Robot_Communication_Manual-(E).pdf](<docs/Robot_Communication_Manual-(E).pdf>) — HIWIN *Robot Communication User Manual* (C25UE801-2211)
- 본 트랙은 위 매뉴얼을 학습 목적으로 재구성한 **교육용 자료**입니다. 매뉴얼 및 제품명(HIWIN, HRSS, Caterpillar, XEG 등)의 권리는 HIWIN에 있습니다.
