# 과제 - 01. 실습 환경 준비

## 문제 1 — 의존성 자가진단
- 파일명: `homework_01/main.py`
- 핵심 개념: 모듈 import, 예외 처리

### 요구사항
- Python 버전을 출력한다.
- `pymodbus`와 `pyserial`을 import 해보고, 성공하면 버전을, 실패하면 친절한 설치 안내를 출력한다.
- 모두 정상이면 마지막 줄에 `READY`를, 하나라도 실패하면 `NOT READY`를 출력한다.

### 예상 출력
```
Python 3.12.10
pymodbus 3.6.9
pyserial 3.5
READY
```

### 힌트
- `import sys; sys.version_info` 로 버전 비교.
- `try: import pymodbus / except ImportError:` 로 누락을 감지.

---

## 문제 2 — 좌표 변환 왕복 검증
- 파일명: `homework_02/main.py`
- 핵심 개념: `_shared` import 부트스트랩, 32bit 분할/복원

### 요구사항
- `_shared/word_tools.py`의 `split_word` / `combine_word`를 불러온다.
- 좌표 `123.456 mm`(×1000 = 123456)를 Low/High word로 **분할**한 뒤 다시 **복원**해, 원래 값과 같은지 확인한다.
- `+123.456`과 `-123.456` 두 경우 모두 검증하고, 각각 `OK`/`FAIL`을 출력한다.

### 예상 출력
```
+123.456 mm -> Low=-7616, High=1 -> 복원 123.456  OK
-123.456 mm -> Low=7616, High=-2 -> 복원 -123.456  OK
```

### 힌트
- main.py 최상단에 `_shared` 탐색 부트스트랩 6줄을 넣어야 import 가 된다.
- `raw = round(mm * 1000)` 후 `split_word(raw)`, 복원은 `combine_word(low, high) / 1000`.

## 정답 확인
직접 풀어 본 후 [`answer/`](./answer/) 폴더의 정답과 비교해 보세요. 정답 파일에는 핵심 포인트와 흔한 실수가 주석으로 정리되어 있습니다.
