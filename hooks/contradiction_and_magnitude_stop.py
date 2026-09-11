#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sys
import tempfile

_RATE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:proteins?\s*)?(?:/|per\s+|a\s+)\s*(min|minute|hour|hr|day)\b", re.I)
_COUNT = re.compile(r"(\d[\d,]{3,})\s+(?:distinct\s+)?(proteins?|genes?|rows?|hits?|records?)\b", re.I)

_PER_MIN = {"min": 1.0, "minute": 1.0, "hour": 1 / 60.0, "hr": 1 / 60.0, "day": 1 / 1440.0}


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _rates(text: str):
    out = []
    for m in _RATE.finditer(text or ""):
        unit = m.group(2).lower()
        out.append((_num(m.group(1)) * _PER_MIN.get(unit, 1.0), m.group(0)))
    return out


def _counts(text: str):
    return [(_num(m.group(1)), m.group(2).lower(), m.group(0)) for m in _COUNT.finditer(text or "")]


# Read a bounded tail, expanding until relevant text records are found.
_TAIL_CAP = 64 * 1024 * 1024


def _tail_records(path: str, want_types=("user", "assistant"), cap: int = _TAIL_CAP):
    """Parsed records from the end of a .jsonl transcript, in forward order.

    Expands the window until it holds a record of every type in `want_types`, or `cap` is reached.
    A window that never reaches a `user` record simply yields no user text, which makes the
    rate-comparison fail open — the same outcome as a transcript with no user rate in it.
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return []
    chunk, pos, buf = min(1 << 20, max(int(cap), 0)), size, b""  # `cap` bounds the read, so honour it first
    while True:
        step = min(chunk, pos, max(0, cap - len(buf)))
        pos -= step
        try:
            with open(path, "rb") as fh:
                fh.seek(pos)
                buf = fh.read(step) + buf
        except OSError:
            return []
        lines = buf.split(b"\n")
        body = lines if pos == 0 else lines[1:]  # a partial first line is dropped unless at BOF
        recs = []
        for raw in body:
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
                if isinstance(record, dict):
                    recs.append(record)
            except Exception:
                continue
        def has_text(record):
            message = record.get("message")
            if not isinstance(message, dict):
                return False
            content = message.get("content", [])
            if isinstance(content, str):
                return bool(content.strip())
            return isinstance(content, list) and any(
                isinstance(item, dict) and item.get("type") == "text"
                and isinstance(item.get("text"), str) and item["text"].strip()
                for item in content)
        have = {r.get("type") for r in recs if has_text(r)}
        if step == 0 or pos == 0 or all(t in have for t in want_types) or len(buf) >= cap:
            return recs
        chunk = min(chunk * 2, 16 << 20)


def _last_messages(transcript_path: str):
    user_txt, asst_txt = "", ""
    try:
        for rec in _tail_records(transcript_path):
            role = rec.get("type")
            content = rec.get("message", {}).get("content", [])
            if isinstance(content, str):
                text = content
            else:
                text = "".join(p.get("text", "") for p in content
                               if isinstance(p, dict) and p.get("type") == "text")
            if not text.strip():
                continue
            if role == "user":
                user_txt, asst_txt = text, ""   # a new user turn resets the assistant side
            elif role == "assistant":
                asst_txt = text
    except Exception:
        return "", ""
    return user_txt, asst_txt


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tpath = payload.get("transcript_path")
    if not tpath or not os.path.isfile(tpath):
        return 0
    user_txt, asst_txt = _last_messages(tpath)
    if not asst_txt:
        return 0

    problems = []

    user_rates = _rates(user_txt)
    asst_rates = _rates(asst_txt)
    if user_rates and asst_rates:
        u = max(r for r, _ in user_rates)
        for a, raw_a in asst_rates:
            if u > 0 and a > 0 and (a / u >= 3.0 or u / a >= 3.0):
                _, raw_u = max(user_rates, key=lambda x: x[0])
                problems.append(
                    f"You state {raw_a} while the user just stated {raw_u} — a {max(a/u, u/a):.1f}x "
                    f"disagreement. The user has watched this system directly. Before explaining their "
                    f"number away, re-check YOUR units and denominator.")
                break

    cs = _counts(asst_txt)
    if len(cs) >= 2:
        universe = [(v, raw) for v, noun, raw in cs if noun.startswith("gene")]
        totals = [(v, raw) for v, noun, raw in cs if noun.startswith("protein")]
        for tv, traw in totals:
            for uv, uraw in universe:
                if uv > 0 and tv > uv * 1.5:
                    problems.append(
                        f"'{traw}' exceeds '{uraw}' named in the same message. A cumulative count "
                        f"cannot exceed the universe it is drawn from — check whether the two are in "
                        f"the same units.")
                    break
            if problems and problems[-1].startswith("'"):
                break

    if not problems:
        return 0

    h = hashlib.sha256(asst_txt.encode("utf-8", "ignore")).hexdigest()[:16]
    marker = os.path.join(tempfile.gettempdir(), f".contradiction_{h}")
    if os.path.exists(marker):
        return 0
    try:
        open(marker, "w").close()
    except Exception:
        pass

    reason = ("NUMERIC CONTRADICTION CHECK (Stop hook) — do not send yet:\n  - "
              + "\n  - ".join(problems)
              + "\n\nThis is not a request to think harder; it is a specific arithmetic conflict. "
                "Re-derive the number, verify what the source field actually counts, and either "
                "correct your figure or state plainly why the user's differs. Receipts alone do not "
                "make a number right — a well-cited value with the wrong units is still wrong.")
    try:
        print(json.dumps({"decision": "block", "reason": reason}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
