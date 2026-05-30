# 과제 - 05. MODBUS 기초

> 두 문제 모두 **터미널 A에 슬레이브** 를 먼저 띄운 뒤 실행합니다.
> `python ../../_shared/robot_server_sim.py --port 1502 --host 127.0.0.1`

## 문제 1 — Holding Register 읽기 → 쓰기 → 재확인
- 파일명: `homework_01/main.py`
- 핵심 개념: R/W 레지스터 쓰기(FC06), "쓰고-되읽어-확인"

### 요구사항
- `from modbus_master import RobotMaster` 로 마스터를 만든다(`--host 127.0.0.1`, `--port 1502`).
- 속도 설정값 **Holding Register 주소 100** 을 먼저 읽어 출력한다.
- `write_holding(100, 75)` 로 값을 쓴 뒤, 다시 읽어 **75 가 반영됐는지** `OK`/`FAIL` 로 확인한다.

### 예상 출력 (슬레이브를 막 띄운 직후 기준)
```
쓰기 전  read_holding(100) = 0
write_holding(100, 75)  완료
쓰기 후  read_holding(100) = 75  OK
```

### 힌트
- `read_holding` 은 리스트를 돌려준다. 단일 값은 `m.read_holding(100, 1)[0]` 으로 꺼낸다.
- main.py 최상단에 `_shared` 탐색 부트스트랩 6줄이 있어야 `modbus_master` 를 import 할 수 있다.
- "쓰기 전" 값은 이전 실습에서 이미 썼다면 0이 아닐 수 있다. 슬레이브를 재시작하면 0으로 돌아간다.

---

## 문제 2 — 읽기 전용 레지스터에는 쓸 수 없음을 확인
- 파일명: `homework_02/main.py`
- 핵심 개념: 읽기/쓰기 권한 강제, 예외 처리

### 요구사항
- **Input Register**(예: 주소 524, 동작상태)와 **Discrete Input**(예: 주소 3, SO4)에 쓰기를 **시도** 한다.
- 이 둘은 읽기 전용이라 `RobotMaster` 에 `write_input`/`write_discrete` 메서드가 **없다**. 호출 시도를 `try/except`(또는 `getattr` 로 존재 확인)로 잡아 "읽기 전용이라 쓸 수 없음" 을 친절히 출력한다.
- 대비로, **Holding Register**(R/W)에는 정상적으로 써지는 것을 함께 보여 권한 차이를 확인한다.

### 예상 출력
```
[1] 읽기 전용 레지스터에 쓰기 시도 — 실패해야 정상입니다.
  [차단] input 은 읽기 전용 → write_input() 메서드가 없습니다. (설계상 정상)
  [차단] discrete 은 읽기 전용 → write_discrete() 메서드가 없습니다. (설계상 정상)
     읽기 전용 값은 그대로 유지됩니다:
       read_input(524,1)  = [1]
       read_discrete(0,8) = [0, 0, 0, 1, 0, 0, 0, 0]

[2] 대비 — R/W 레지스터(Holding)는 정상적으로 써집니다.
     write_holding(100, 60) 후 read_holding(100,1) = [60]  OK

결론: 권한 표(DI·IR=R, Coil·HR=R/W)가 실제로 강제됩니다.
```

### 힌트
- `getattr(m, "write_input", None)` 이 `None` 이면 쓰기 메서드가 없는 것 — 이것이 곧 "읽기 전용" 의 증거다.
- 읽기 전용 레지스터에 쓰기 Function Code(05/06/15/16)는 존재하지 않는다. 02·04(읽기)만 있다.
- 이는 버그가 아니라 **설계** 다. 이 값들은 슬레이브(로봇)가 채우므로 마스터는 읽기만 한다.

## 정답 확인
직접 풀어 본 후 [`answer/`](./answer/) 폴더의 정답과 비교해 보세요. 정답 파일에는 핵심 포인트와 흔한 실수가 주석으로 정리되어 있습니다.
