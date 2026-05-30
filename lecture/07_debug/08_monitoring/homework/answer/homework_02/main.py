"""
정답 2 — 값 리스트를 10h(Write Multiple Registers) 요청 프레임으로 인코딩 (역방향)

핵심 포인트:
- 손해독(decode)의 반대 방향. 시작주소와 값 리스트로 Master 송신 프레임을 만든다.
- 10h 요청 = [FC=10][시작주소(2)][개수(2)][byte수(1)][값들(개수×2)].
- byte수 = 개수 × 2 (Word 규칙). 각 값은 big-endian 2바이트로 분해: (v>>8), (v&0xFF).
- 만든 프레임을 다시 디코드하면 원래 (시작주소, 값) 이 그대로 복원되어야 한다(왕복 검증).

흔한 실수:
- byte수 칸을 빠뜨리는 것(10h 송신에는 반드시 있다. 응답 에코에는 없다).
- 16bit 를 넘는 값을 & 0xFFFF 없이 넣어 3바이트로 새는 것.
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


def encode_write_multiple(start, values):
    """시작주소 + 값 리스트 -> 10h 요청 프레임 hex 문자열."""
    count = len(values)
    byte_count = count * 2
    frame = [0x10, (start >> 8) & 0xFF, start & 0xFF,
             (count >> 8) & 0xFF, count & 0xFF, byte_count]
    for v in values:
        v &= 0xFFFF  # 16bit 로 안전하게 자름
        frame += [(v >> 8) & 0xFF, v & 0xFF]
    return " ".join(f"{b:02X}" for b in frame)


def decode_write_multiple(text):
    """왕복 검증용: 10h 요청 프레임 -> (시작주소, 값 리스트)."""
    b = [int(p, 16) for p in text.split()]
    start = (b[1] << 8) | b[2]
    count = (b[3] << 8) | b[4]
    payload = b[6:6 + b[5]]
    values = [(payload[i] << 8) | payload[i + 1] for i in range(0, len(payload), 2)]
    return start, count, values


def main():
    start, values = 201, [111, 222, 333]
    frame = encode_write_multiple(start, values)
    print(f"입력: 시작주소={start}, 값={values}")
    print(f"10h 요청 프레임: {frame}")
    # 기대: 10 00 C9 00 03 06 00 6F 00 DE 01 4D
    assert frame == "10 00 C9 00 03 06 00 6F 00 DE 01 4D", frame

    # 왕복 검증: 다시 디코드하면 원래 값이 나온다.
    d_start, d_count, d_values = decode_write_multiple(frame)
    print(f"재해독: 시작주소={d_start}, 개수={d_count}, 값={d_values}")
    assert (d_start, d_count, d_values) == (201, 3, [111, 222, 333])

    print("인코딩/왕복 검증 완료 ✅")


if __name__ == "__main__":
    main()
