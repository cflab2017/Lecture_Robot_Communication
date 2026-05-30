"""
04. RS-232 직렬 통신 — 패킷 프레이밍 데모 (serial_comm)

com0com 가상 COM 포트나 실제 시리얼 케이블은 자동 검증 환경에 없으므로,
이 데모는 *하드웨어 없이* RS-232 패킷 포맷만 순수 Python 으로 재현한다.

핵심:
  - HIWIN 패킷 포맷 = 시작/끝을 중괄호 { } 로 감싸고, 값은 콤마 , 로 구분.
    예) [123, 456]  ->  "{123,456}"  ->  파싱  ->  [123, 456]
  - non-format(시작/끝/구분 기호 없음) = 데이터를 ASCII CODE(10진수) 1바이트씩 해석.
    예) "AB"  ->  [65, 66]  (A=65, B=66)
  - 이 포맷·명령(CWRITE/CREAD)은 TCP/IP(03편)와 동일하다. 물리 계층과
    COPEN 의 첫 인자(ETH -> SER)만 바뀐다.

실제 시리얼 송수신 실습은 com0com + _shared/serial_echo.py + serial_client.py 로
README 의 단계 안내를 따른다. 이 main.py 는 포트가 필요 없다.

실행:
    python src/serial_comm/main.py
"""
import os
import sys

# --- _shared 공유 라이브러리 경로 추가 (편 위치·깊이와 무관하게 상위에서 _shared 탐색) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "_shared")):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, "_shared"))

# cp949 콘솔에서도 한글/기호가 깨지거나 죽지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def encode_packet(values) -> str:
    """정수 리스트를 HIWIN 포맷 패킷 문자열로 인코딩한다 (CWRITE 가 보낼 모양).

    [123, 456]  ->  "{123,456}"
    """
    return "{" + ",".join(str(v) for v in values) + "}"


def decode_packet(packet: str) -> list:
    """HIWIN 포맷 패킷 문자열을 정수 리스트로 디코딩한다 (CREAD 가 받은 모양).

    "{123,456}"  ->  [123, 456]
    """
    body = packet.strip().strip("{}")     # 앞뒤 { } 제거
    if not body:
        return []
    return [int(tok) for tok in body.split(",")]


def encode_nonformat(text: str) -> list:
    """non-format: 문자열을 ASCII CODE(10진수) 리스트로 인코딩한다.

    "AB"  ->  [65, 66]
    """
    return [ord(ch) for ch in text]


def decode_nonformat(codes) -> str:
    """non-format: ASCII CODE(10진수) 리스트를 문자열로 디코딩한다.

    [65, 66]  ->  "AB"
    """
    return "".join(chr(c) for c in codes)


def main():
    print("=== RS-232 패킷 프레이밍 데모 (하드웨어 불필요) ===")

    # 1) format 모드 — { } 로 감싸고 , 로 구분 (CWRITE/CREAD 가 쓰는 포맷)
    values = [123, 456]
    packet = encode_packet(values)                 # CWRITE 가 보낼 바이트열의 본문
    restored = decode_packet(packet)               # CREAD 가 받아 파싱한 결과
    ok_fmt = restored == values
    print("[1] format 모드 (TCP/IP와 동일)")
    print(f"    값 {values}  -> 인코딩 \"{packet}\"  -> 디코딩 {restored}  "
          f"{'OK' if ok_fmt else 'FAIL'}")

    # 여러 값도 동일 규칙 — 콤마로 계속 이어붙는다
    triple = [90000, -45100, 30]
    pkt3 = encode_packet(triple)
    ok_fmt3 = decode_packet(pkt3) == triple
    print(f"    값 {triple}  -> \"{pkt3}\"  -> {decode_packet(pkt3)}  "
          f"{'OK' if ok_fmt3 else 'FAIL'}")

    # 2) non-format 모드 — 시작/끝/구분 기호 없이 ASCII 10진수 1바이트씩
    text = "AB"
    codes = encode_nonformat(text)                 # 문자 -> ASCII CODE
    back = decode_nonformat(codes)                 # ASCII CODE -> 문자
    ok_nf = back == text
    print("[2] non-format 모드 (ASCII decimal)")
    print(f"    문자열 \"{text}\"  -> 코드 {codes}  -> 복원 \"{back}\"  "
          f"{'OK' if ok_nf else 'FAIL'}")

    print("-" * 30)
    all_ok = ok_fmt and ok_fmt3 and ok_nf
    print("패킷 프레이밍 왕복 검증 통과 ✅" if all_ok
          else "패킷 프레이밍 검증 실패 ❌")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
