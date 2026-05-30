"""
정답 1 — 주어진 hex 프레임 손해독

핵심 포인트:
- Modbus 프레임은 [Function Code][Data] 구조. 첫 바이트가 FC.
- 읽기 응답(03/04)은 [byte수(1)][레지스터값...]. byte수 = 개수 × 2.
- Word 값은 상위바이트·하위바이트 2개를 합쳐 16bit 정수로 만든다: (hi<<8)|lo.
- 03h 응답 `03 06 00 64 00 00 04 4E` => byte수 6 => 레지스터 3개 => [100, 0, 1102].

흔한 실수:
- byte수(=개수×2)와 레지스터 개수를 혼동하는 것. byte 6은 레지스터 3개다.
- High/Low 바이트 순서를 뒤집어 0x6400(=25600)처럼 잘못 합치는 것. Modbus는 big-endian(상위 먼저).
"""
import os
import sys

# _shared 탐색 부트스트랩 (깊이 무관)
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "_shared")):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, "_shared"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_hex(text):
    return [int(p, 16) for p in text.split()]


def u16(hi, lo):
    return (hi << 8) | lo


def decode_read_response(text):
    """읽기 응답(03h/04h): [FC][byte수][레지스터값...] 를 해석한다."""
    b = parse_hex(text)
    fc, byte_count = b[0], b[1]
    payload = b[2:2 + byte_count]
    values = [u16(payload[i], payload[i + 1]) for i in range(0, byte_count, 2)]
    return fc, byte_count, values


def decode_request(text):
    """읽기 요청(02h/03h/04h): [FC][시작주소(2)][개수(2)] 를 해석한다."""
    b = parse_hex(text)
    fc = b[0]
    start = u16(b[1], b[2])
    count = u16(b[3], b[4])
    return fc, start, count


def main():
    # 프레임 1 — 요청 04h (Read Input Registers)
    fc, start, count = decode_request("04 01 90 00 02")
    print(f"[1] 요청 FC=0x{fc:02X}, 시작주소={start}(0x{start:04X}), 개수={count}")
    assert (fc, start, count) == (0x04, 400, 2)

    # 프레임 2 — 응답 03h (Read Holding Registers), byte수 6 => 레지스터 3개
    fc, bc, values = decode_read_response("03 06 00 64 00 00 04 4E")
    print(f"[2] 응답 FC=0x{fc:02X}, byte수={bc}, 값={values}")
    assert (fc, bc, values) == (0x03, 6, [100, 0, 1102])

    print("프레임 해독 완료 ✅")


if __name__ == "__main__":
    main()
