"""Inspect a death and redact secrets before any model sees them."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

@dataclass
class TraceFrame:
    file: str
    line: int
    function: str
    source: str | None

    def to_dict(self):
        return asdict(self)

@dataclass
class ExceptionInfo:
    type: str | None
    message: str

    def to_dict(self):
        return asdict(self)

@dataclass
class Facts:
    id: str
    argv: list[str]
    cwd: str
    duration_ms: int
    exit_code: int
    signal: int | None
    signal_name: str | None
    timed_out: bool
    cause_class: str
    exception: ExceptionInfo
    frames: list[TraceFrame]
    last_words: str
    redactions: dict[str, int]
    language: str

    def to_dict(self):
        d = asdict(self)
        d["exception"] = self.exception.to_dict()
        d["frames"] = [f.to_dict() for f in self.frames]
        return d

def _redact(text: str) -> tuple[str, dict[str, int]]:
    if not text:
        return text, {}
    counts: dict[str, int] = {}

    def sub(pattern, repl, kind):
        nonlocal text
        text, n = re.subn(pattern, repl, text)
        if n:
            counts[kind] = counts.get(kind, 0) + n
        return text

    sub(r'(?i)(authorization\s*:\s*(?:bearer|token)\s+)[^\s"\']+', r'\1[redacted:token]', "token")
    sub(r'(?i)((?:api[_-]?key|apikey|secret|passwd|password)\s*[:=]\s*)\S+', r'\1[redacted]', "secret")
    sub(r'\b(sk|ghp|gho|ghu|ghs|ghr|AKIA|ASIA|xox[baprs]|pat[-_])[A-Za-z0-9_-]{8,}\b', '[redacted:key]', "key")
    sub(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b', '[redacted:jwt]', "jwt")
    sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[redacted:email]', "email")
    sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[redacted:ip]', "ip")
    sub(r'/home/[^\s/:]+', '/home/[user]', "path")
    sub(r'C:\\Users\\[^\s\\:]+', r'C:\\Users\\[user]', "path")
    sub(r'\b[0-9a-fA-F]{32,}\b', '[redacted:hex]', "hex")

    return text, counts

def _extract_python_traceback(stderr: str) -> tuple[ExceptionInfo, list[TraceFrame]]:
    lines = stderr.splitlines()
    frames: list[TraceFrame] = []
    for i, line in enumerate(lines):
        m = re.match(r'\s*File "([^"]+)", line (\d+), in (.+)', line)
        if m:
            path = m.group(1)
            ln = int(m.group(2))
            func = m.group(3).strip()
            src = None
            try:
                with open(path, errors="replace") as f:
                    all_lines = f.readlines()
                if 1 <= ln <= len(all_lines):
                    src = all_lines[ln - 1].rstrip()
            except Exception:
                pass
            if src is None and i + 1 < len(lines):
                nxt = lines[i + 1]
                if nxt and not nxt.strip().startswith("File ") and not re.match(r'\s*\w+Error|^\S+:', nxt):
                    src = nxt.strip()
            frames.append(TraceFrame(file=path, line=ln, function=func, source=src))

    exc = ExceptionInfo(type=None, message="")
    for line in reversed(lines):
        line = line.strip()
        if not line or line.startswith("File ") or line.startswith("^"):
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Interrupt|Exit))(?::\s*(.*))?$', line)
        if m:
            exc = ExceptionInfo(type=m.group(1), message=(m.group(2) or "").strip())
            break
    if exc.type is None and frames:
        exc = ExceptionInfo(type="Exception", message="")
    return exc, frames

def _classify(language: str, death, exc: ExceptionInfo) -> str:
    if death.signal_name:
        return "signal"
    if exc.type:
        return "exception"
    if death.exit_code != 0:
        return "exit"
    return "exit"

def examine(death) -> Facts:
    err = getattr(death, "stderr", "") or ""
    out = getattr(death, "stdout", "") or ""
    err_red, r1 = _redact(err)
    out_red, r2 = _redact(out)
    counts = dict(r1)
    for k, v in r2.items():
        counts[k] = counts.get(k, 0) + v

    combined = err_red + "\n" + out_red
    language = "unknown"
    argv = getattr(death, "argv", []) or []
    argv0 = argv[0] if argv else ""
    if argv0.endswith(".py") or "python" in argv0:
        language = "python"

    exc, frames = _extract_python_traceback(err_red)
    if frames and language == "unknown":
        if any(f.file.endswith(".py") for f in frames):
            language = "python"
        elif any(f.file.endswith(".c") for f in frames):
            language = "c"

    last_words = ""
    for line in reversed(err_red.splitlines()):
        s = line.rstrip()
        if s.strip():
            last_words = s.strip()
            break
    if not last_words:
        for line in reversed(out_red.splitlines()):
            s = line.rstrip()
            if s.strip():
                last_words = s.strip()
                break

    cause_class = _classify(language, death, exc)

    death_id = getattr(death, "id", None)
    if death_id is None:
        import hashlib, time

        h = hashlib.sha256()
        h.update(str(argv).encode())
        h.update((last_words or "")[:200].encode())
        death_id = "requiem-" + h.hexdigest()[:6]

    return Facts(
        id=death_id,
        argv=argv,
        cwd=getattr(death, "cwd", ""),
        duration_ms=getattr(death, "duration_ms", 0),
        exit_code=getattr(death, "exit_code", 0),
        signal=getattr(death, "signal", None),
        signal_name=getattr(death, "signal_name", None),
        timed_out=getattr(death, "timed_out", False),
        cause_class=cause_class,
        exception=exc,
        frames=frames,
        last_words=last_words,
        redactions=counts,
        language=language,
    )
