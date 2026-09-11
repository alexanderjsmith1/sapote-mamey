#!/usr/bin/env python3
import sys, json, os, re, hashlib, tempfile

RISK = re.compile(r"\b(no such file|does not exist|doesn'?t exist|there (?:is|are) no|"
                  r"confirmed|verified|exactly \d|all \d+|\d+\s*/\s*\d+)\b", re.I)
# Receipt matching remains deliberately permissive to avoid routine false blocks.
RECEIPT = re.compile(r"(on disk|register|receipt|sha|\.tsv|\.csv|\.json|`[^`]+`|let me check|"
                     r"unverified|verified against|per (?:the )?\w+\.(?:py|tsv|csv|json))", re.I)

# Read a bounded tail, expanding until relevant text records are found.
_TAIL_CAP = 64 * 1024 * 1024


def tail_records(tpath, want_types=("assistant",), cap=_TAIL_CAP):
    """Parsed records from the end of a .jsonl transcript, in forward order.

    Expands the window until it holds a record of every type in `want_types`, or `cap` is reached.
    Returns [] on any read/parse failure so callers fail open exactly as before.
    """
    try:
        size = os.path.getsize(tpath)
    except OSError:
        return []
    chunk, pos, buf = min(1 << 20, max(int(cap), 0)), size, b""  # `cap` bounds the read, so honour it first
    while True:
        step = min(chunk, pos, max(0, cap - len(buf)))
        pos -= step
        try:
            with open(tpath, "rb") as fh:
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


def last_assistant_text(tpath):
    txt = ""
    try:
        for rec in tail_records(tpath, ("assistant",)):
            if rec.get("type") == "assistant":
                parts = rec.get("message", {}).get("content", [])
                t = "".join(p.get("text", "") for p in parts
                            if isinstance(p, dict) and p.get("type") == "text")
                if t.strip():
                    txt = t
    except Exception:
        return ""
    return txt


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tpath = payload.get("transcript_path")
    if not tpath or not os.path.isfile(tpath):
        return 0
    text = last_assistant_text(tpath)
    if not text or not RISK.search(text) or RECEIPT.search(text):
        return 0
    h = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]
    marker = os.path.join(tempfile.gettempdir(), f".selfaudit_{h}")
    if os.path.exists(marker):
        return 0
    try:
        open(marker, "w").close()
    except Exception:
        pass
    reason = ("SELF-AUDIT (Stop hook): this reply asserts a fact/count/existence-negative with no "
              "visible receipt (path, code span, count, SHA, or 'on disk'). Before it lands: did you "
              "verify it against disk THIS turn? If yes, cite the evidence inline; if not, run the "
              "cheap check or hedge it. Re-answer once each claim carries its receipt.")
    try:
        print(json.dumps({"decision": "block", "reason": reason}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
