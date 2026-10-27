"""Run a program and record how it died."""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass

@dataclass
class Death:
    id: str
    argv: list[str]
    cwd: str
    started_at: str
    duration_ms: int
    exit_code: int
    signal: int | None
    signal_name: str | None
    stderr: str
    stdout: str
    timed_out: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

def _make_id(argv: list[str], stderr: str, started: float) -> str:
    h = hashlib.sha256()
    h.update(" ".join(argv).encode())
    h.update(stderr[-2000:].encode())
    h.update(str(int(started)).encode())
    return "requiem-" + h.hexdigest()[:6]

def run(argv: list[str], timeout: float = 30.0, tail: int = 4000) -> Death:
    """Run argv to completion and return the death record.

    stderr and stdout are truncated to the last `tail` characters so a chatty
    program cannot bury the interesting line or blow up the model prompt.
    """
    if not argv:
        raise SystemExit("requiem: nothing to run")

    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        code, out, err = proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        raise SystemExit(f"requiem: {argv[0]}: command not found") from None
    except PermissionError:
        raise SystemExit(f"requiem: {argv[0]}: permission denied") from None
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        code = -9
        out = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace")
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
        if not isinstance(out, str):
            out = ""
        if not isinstance(err, str):
            err = ""
        err += f"\nrequiem: killed after {timeout}s\n"

    duration_ms = int((time.time() - started) * 1000)
    sig = -code if code < 0 else None
    sig_name = None
    if sig is not None:
        try:
            sig_name = signal.Signals(sig).name
        except ValueError:
            sig_name = f"SIG{sig}"

    return Death(
        id=_make_id(argv, err or "", started),
        argv=argv,
        cwd=os.getcwd(),
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        duration_ms=duration_ms,
        exit_code=code,
        signal=sig,
        signal_name=sig_name,
        stderr=(err or "")[-tail:],
        stdout=(out or "")[-tail:],
        timed_out=timed_out,
    )
