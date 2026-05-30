# 과제 - 06. MODBUS SERVER (로봇 = 슬레이브)

> 선행: 두 과제 모두 다른 터미널에서 로봇 슬레이브를 먼저 띄워 둡니다.
> ```powershell
> cd lecture/_shared
> set PYTHONUTF8=1
> python robot_server_sim.py --port 1502 --host 127.0.0.1
> ```

## 문제 1 — GO HOME 명령 사이클
- 파일명: `homework_01/main.py`
- 핵심 개념: 파라미터 없는 명령, 명령 실행 5단계

### 요구사항
- 명령 번호 **4(GO HOME)** 를 `HR[201]`에 쓰고 명령 사이클을 한 번 돈다.
  GO HOME은 파라미터가 명령 번호 1개뿐이라 가장 단순하다.
- `HR[200]=1` 로 트리거한 뒤, `IR[524]=1(Idle)` 이고 `IR[200]=1(Success)` 가 될 때까지 폴링한다.
- 현재 관절 `IR[300:312]` 가 **전부 0** 으로 돌아왔는지 확인하고, 마지막에 `HR[200]=0` 으로 리셋한다.
- `argparse --host(127.0.0.1) --port(1502)` 를 지원한다.

### 예상 출력
```
=== GO HOME 명령 사이클 ===
HR[201]<-4(GO HOME), HR[200]<-1  트리거
완료: IR[524]=1(Idle), IR[200]=1(Success)
현재 관절 IR[300:312] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  (모두 0)
HR[200]<-0  리셋
GO HOME 완료 ✅
```

### 힌트
- `from modbus_master import RobotMaster` 로 마스터를 가져온다.
- GO HOME은 파라미터가 없으므로 `m.write_holding(201, 4)` 한 줄이면 ①②가 끝난다.
- 폴링 조건: `m.read_input(524, 1)[0] == 1 and m.read_input(200, 1)[0] == 1`.

---

## 문제 2 — 직교 LIN 으로 X=-300mm 이동 후 좌표 복원
- 파일명: `homework_02/main.py`
- 핵심 개념: Cartesian 모션, 음수 좌표의 word 인코딩, 응답값 복원

### 요구사항
- 명령 번호 **1(LIN)**, 모션 타입 **1(Cartesian)** 으로 **X = -300.000mm** 직선 이동을 명령한다.
- `split_word(-300000)` 는 `(27680, -5)` 로 High word가 **음수**다.
  `RobotMaster.write_holding()` 이 음수 word를 `& 0xFFFF` 로 자동 인코딩하므로 그대로 넣으면 된다.
- 명령 사이클 완료 후 직교 X의 `IR[400:402]` 를 읽어, **signed 로 복원**해 `-300.000mm` 가 맞는지 확인한다.
- `argparse --host(127.0.0.1) --port(1502)` 를 지원한다.

### 예상 출력
```
=== 직교 LIN 명령 사이클 (X=-300mm) ===
HR[201]<-1(LIN), HR[202]<-1(Cartesian), HR[203:205]=[27680, -5]  (split_word(-300000))
HR[200]<-1  트리거
완료: IR[524]=1(Idle), IR[200]=1(Success)
직교 X IR[400:402] (raw, unsigned) = [27680, 65531]
signed 복원 = (27680, -5)  ->  -300000  ->  -300.000 mm
HR[200]<-0  리셋
LIN 사이클 완료 ✅
```

### 힌트
- 파라미터: `[1, 1, X_low, X_high, 0,0,0,0,0,0,0,0,0,0, 50, 100, 1, 2]` (Y~C=0).
- 응답은 unsigned 로 읽히므로(`65531`), `raw - 65536 if raw > 32767 else raw` 로 signed 복원한다.
- 복원: `high*65536 + (low & 0xFFFF)` (= `combine_word`), 공학값은 `×0.001`.

## 정답 확인
직접 풀어 본 후 [`answer/`](./answer/) 폴더의 정답과 비교해 보세요. 정답 파일에는 핵심 포인트와 흔한 실수가 주석으로 정리되어 있습니다.
