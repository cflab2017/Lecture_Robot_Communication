"""
08. 모니터링 & 디버깅 — Modbus 프레임 손해독기 (modbus_monitor)

하드웨어·Wireshark 없이도 자동 검증되도록, 이 스크립트는 순수 Python 으로
Modbus 패킷의 알맹이(Function Code + Data)를 사람이 읽게 풀어 주는 도구다.
HRSS/Caterpillar Modbus Monitor 화면이나 Wireshark 상세 트리에 16진수로
보이는 프레임을 그대로 입력하면, 시작주소·개수·byte수·데이터를 해석한다.

매뉴얼 Ch.5.5.2 의 송수신 포맷과 손계산 예제 3종을 그대로 검증한다.
표준 라이브러리만 사용하며 포트/장비가 필요 없다.

실행:  python src/modbus_monitor/main.py
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


# Function Code 이름표 (매뉴얼 5.5.2)
FC_NAMES = {
    0x02: "Read Discrete Inputs",
    0x01: "Read Coils",
    0x0F: "Write Multiple Coils",
    0x04: "Read Input Registers",
    0x03: "Read Holding Registers",
    0x10: "Write Multiple Registers",
    0x06: "Write Single Register",
}

# 데이터 종류: 읽기 응답이 Bit(상태 byte) 인지 Word(레지스터) 인지
BIT_FC = {0x01, 0x02, 0x0F}     # Coil / Discrete Input
WORD_FC = {0x03, 0x04, 0x10, 0x06}  # Holding / Input Register


def parse_hex(text):
    """'02 01 2C 00 05' 또는 '02012C0005' 같은 16진 문자열을 바이트 리스트로."""
    cleaned = text.replace("0x", "").replace(",", " ")
    parts = cleaned.split()
    if len(parts) == 1 and len(parts[0]) % 2 == 0:
        # 공백 없이 붙은 경우 2글자씩 잘라 읽는다.
        s = parts[0]
        parts = [s[i:i + 2] for i in range(0, len(s), 2)]
    return [int(p, 16) for p in parts]


def _u16(hi, lo):
    """상위/하위 바이트 2개를 부호 없는 16bit 정수로."""
    return (hi << 8) | lo


def decode_frame(text, kind="auto"):
    """Modbus 프레임(Function Code + Data, 16진 문자열)을 해석해 dict 로 돌려준다.

    kind:
      - "request"  : Master 송신(요청)으로 해석
      - "response" : Slave 응답으로 해석
      - "auto"     : 길이·구조로 요청/응답을 추정 (실습 검증용)

    돌려주는 dict 의 핵심 키:
      fc, fc_name, role("request"/"response"), 그리고 FC별 필드
      (start, count, byte_count, values, bits ...) + lines(사람용 설명 줄 리스트)
    """
    data = parse_hex(text)
    if not data:
        raise ValueError("빈 프레임입니다.")

    fc = data[0]
    fc_name = FC_NAMES.get(fc, f"Unknown(0x{fc:02X})")
    body = data[1:]
    out = {"fc": fc, "fc_name": fc_name, "raw": data}
    lines = [f"FC=0x{fc:02X} ({fc_name})"]

    # --- 에러 응답: FC 최상위 비트가 1 (예: 0x82, 0x83) ---
    if fc & 0x80:
        base = fc & 0x7F
        exc = body[0] if body else None
        exc_name = {
            0x01: "Illegal Function",
            0x02: "Illegal Data Address",
            0x03: "Illegal Data Value",
        }.get(exc, "?")
        out.update(role="exception", base_fc=base, exception=exc)
        lines = [
            f"에러 응답! 원래 FC=0x{base:02X}, "
            f"Exception Code=0x{exc:02X} ({exc_name})"
        ]
        out["lines"] = lines
        return out

    role = _guess_role(fc, body) if kind == "auto" else kind
    out["role"] = role

    if fc in BIT_FC or fc in WORD_FC:
        if role == "request":
            _decode_request(fc, body, out, lines)
        else:
            _decode_response(fc, body, out, lines)
    else:
        lines.append(f"미지원 FC, raw={_hexs(body)}")

    out["lines"] = lines
    return out


def _guess_role(fc, body):
    """요청/응답 자동 추정. 쓰기(0F/10)는 송신에 byte수가 더 붙어 길이가 길다."""
    if fc in (0x0F, 0x10):
        # 요청: 시작(2)+개수(2)+byte수(1)+데이터(>=2) -> 7바이트 이상
        # 응답: 시작(2)+개수(2) -> 정확히 4바이트
        return "response" if len(body) == 4 else "request"
    if fc == 0x06:
        return "request"  # 06h는 요청/응답 형식이 동일(주소2+값2)
    # 읽기(01/02/03/04): 요청은 시작(2)+개수(2)=4바이트, 응답은 byte수(1)+데이터
    return "request" if len(body) == 4 else "response"


def _decode_request(fc, body, out, lines):
    start = _u16(body[0], body[1])
    count = _u16(body[2], body[3])
    out.update(role="request", start=start, count=count)
    lines.append(f"시작주소 = 0x{start:04X} = {start}")
    lines.append(f"개수     = {count}")

    if fc in (0x0F, 0x10):  # 다중 쓰기: 데이터까지 실림
        byte_count = body[4]
        payload = body[5:5 + byte_count]
        out["byte_count"] = byte_count
        lines.append(f"byte 수  = {byte_count}")
        if fc == 0x10:  # Word
            values = [_u16(payload[i], payload[i + 1])
                      for i in range(0, len(payload), 2)]
            out["values"] = values
            lines.append(f"값(10진) = {values}")
        else:           # 0Fh Bit
            bits = _bytes_to_bits(payload, count)
            out["bits"] = bits
            lines.append(f"비트     = {bits}")


def _decode_response(fc, body, out, lines):
    if fc in (0x0F, 0x10):  # 쓰기 응답: 시작주소+개수 에코
        start = _u16(body[0], body[1])
        count = _u16(body[2], body[3])
        out.update(role="response", start=start, count=count, echo=True)
        lines.append(f"시작주소(에코) = 0x{start:04X} = {start}")
        lines.append(f"개수(에코)     = {count}")
        return

    if fc == 0x06:  # 단일 쓰기 응답: 주소+값 에코
        addr = _u16(body[0], body[1])
        val = _u16(body[2], body[3])
        out.update(role="response", start=addr, values=[val], echo=True)
        lines.append(f"주소(에코) = 0x{addr:04X} = {addr}")
        lines.append(f"값(에코)   = {val}")
        return

    # 읽기 응답: byte수(1) + 데이터
    byte_count = body[0]
    payload = body[1:1 + byte_count]
    out["byte_count"] = byte_count
    lines.append(f"byte 수  = {byte_count}")
    if fc in WORD_FC:  # 03/04: 레지스터 값
        values = [_u16(payload[i], payload[i + 1])
                  for i in range(0, len(payload), 2)]
        out["values"] = values
        lines.append(f"값(10진) = {values}")
    else:              # 01/02: 비트 상태
        bits = _bytes_to_bits(payload, None)
        out["bits"] = bits
        lines.append(f"비트     = {bits}")


def _bytes_to_bits(payload, count):
    """상태 byte 들을 LSB-first 비트 리스트로. count 가 주어지면 그만큼 자른다."""
    bits = []
    for b in payload:
        for i in range(8):
            bits.append((b >> i) & 1)
    return bits[:count] if count is not None else bits


def encode_write_multiple(start, values):
    """역방향: 시작주소 + 값 리스트 -> 10h(Write Multiple Registers) 요청 프레임 hex.

    homework_02 와 동일한 로직(여기서는 참고용으로 함께 둠).
    """
    byte_count = len(values) * 2
    frame = [0x10, (start >> 8) & 0xFF, start & 0xFF,
             (len(values) >> 8) & 0xFF, len(values) & 0xFF, byte_count]
    for v in values:
        v &= 0xFFFF
        frame += [(v >> 8) & 0xFF, v & 0xFF]
    return " ".join(f"{b:02X}" for b in frame)


def _hexs(bs):
    return " ".join(f"{b:02X}" for b in bs)


def _show(title, text, kind="auto"):
    print(f"--- {title} ---")
    print(f"입력 프레임: {text}")
    res = decode_frame(text, kind)
    for ln in res["lines"]:
        print(f"  {ln}")
    return res


def main():
    print("=== Modbus 프레임 손해독기 ===")

    # ① 요청 02h — Read Discrete Inputs
    r1 = _show("① 요청 02h", "02 01 2C 00 05", "request")
    assert r1["fc"] == 0x02 and r1["start"] == 300 and r1["count"] == 5, r1

    print()
    # ② 응답 04h — Read Input Registers
    r2 = _show("② 응답 04h", "04 04 00 5A 00 00", "response")
    assert r2["fc"] == 0x04 and r2["byte_count"] == 4 and r2["values"] == [90, 0], r2

    print()
    # ③ 요청 10h — Write Multiple Registers
    r3 = _show("③ 요청 10h", "10 00 C9 00 03 06 00 6F 00 DE 01 4D", "request")
    assert r3["fc"] == 0x10 and r3["start"] == 201 and r3["count"] == 3, r3
    assert r3["values"] == [111, 222, 333], r3

    print("-" * 30)
    print("프레임 해독 검증 통과 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
