"""Ask a local open-weight model to write an obituary."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from urllib import request
from urllib.error import URLError

@dataclass
class Obit:
    cause: str
    fix: str | None
    eulogy: str
    model: str
    degraded: bool
    elapsed_ms: int

    def to_dict(self):
        return asdict(self)

class Ghost:
    def __init__(self, base_url: str | None = None, model: str | None = None, cache_dir: str | None = None):
        self.base_url = (base_url or os.environ.get("REQ_SERVER") or "http://127.0.0.1:8099").rstrip("/")
        self.model = model or os.environ.get("REQ_MODEL") or ""
        self.cache_dir = cache_dir or os.environ.get("REQ_CACHE", "data/cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "ghost.jsonl")

    def available(self, timeout: float = 2.0) -> bool:
        try:
            req = request.Request(f"{self.base_url}/health", method="GET")
            with request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            try:
                req = request.Request(f"{self.base_url}/v1/models", method="GET")
                with request.urlopen(req, timeout=timeout) as resp:
                    return resp.status == 200
            except Exception:
                return False

    def _cache_get(self, key: str):
        if not os.path.exists(self.cache_file):
            return None
        try:
            with open(self.cache_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if obj.get("key") == key:
                        return obj.get("value")
        except Exception:
            return None
        return None

    def _cache_set(self, key: str, value):
        try:
            with open(self.cache_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "value": value}) + "\n")
        except Exception:
            pass

    def _chat(self, messages: list[dict], temperature: float = 0.4, max_tokens: int = 200, timeout: float = 180.0):
        payload = {
            "model": self.model or "local-model",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
        obj = json.loads(body)
        content = obj["choices"][0]["message"]["content"]
        if content is None:
            return ""
        return content

    def _facts_to_context(self, facts) -> str:
        f = facts.to_dict() if hasattr(facts, "to_dict") else facts
        lines = []
        lines.append(f"EXIT: {f.get('exit_code')}")
        if f.get("signal_name"):
            lines.append(f"SIGNAL: {f.get('signal_name')} ({f.get('signal')})")
        if f.get("timed_out"):
            lines.append("TIMED_OUT: true")
        exc = f.get("exception") or {}
        if exc.get("type"):
            lines.append(f"EXCEPTION: {exc['type']}: {exc.get('message','')}")
        frames = f.get("frames") or []
        if frames:
            fr = frames[-1]
            lines.append(f"WHERE: {fr.get('file')}:{fr.get('line')} in {fr.get('function')}")
            if fr.get("source"):
                lines.append(f"SOURCE: {fr.get('source')}")
        if f.get("last_words"):
            lines.append(f"LAST_WORDS: {f['last_words']}")
        if f.get("redactions"):
            lines.append(f"REDACTIONS: {json.dumps(f['redactions'])}")
        lines.append(f"LANG: {f.get('language')}")
        lines.append(f"CMD: {' '.join(f.get('argv') or [])}")
        return "\n".join(lines)

    def diagnose(self, facts, temperature: float = 0.0) -> tuple[str, str | None, bool]:
        ctx = self._facts_to_context(facts)
        key = hashlib.sha256(("d" + ctx).encode()).hexdigest()
        cached = self._cache_get(key)
        if cached:
            try:
                c = cached
                return c.get("cause", ""), c.get("fix"), True
            except Exception:
                pass

        system = "You are a crash coroner. Output ONLY valid JSON. Keys: cause, fix. No markdown, no extra text."
        user = (
            "CRASH:\n" + ctx + "\n\n"
            "Return exactly: {\"cause\":\"<<=40 words>\",\"fix\":\"<<=40 words or null\"}\n"
            "Be precise and technical. Do not invent files."
        )
        try:
            content = self._chat([{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=temperature, max_tokens=60)
            import re

            m = re.search(r"\{.*\}", content, re.S)
            if m:
                obj = json.loads(m.group(0))
                cause = str(obj.get("cause") or "").strip()
                fix = obj.get("fix")
                if isinstance(fix, str):
                    fix = fix.strip() or None
                elif fix is None:
                    pass
                else:
                    fix = None
                if cause:
                    self._cache_set(key, {"cause": cause, "fix": fix})
                    return cause, fix, True
        except Exception:
            pass
        f = facts.to_dict() if hasattr(facts, "to_dict") else facts
        exc = f.get("exception") or {}
        frames = f.get("frames") or []
        if f.get("signal_name"):
            where = ""
            if frames:
                fr = frames[-1]
                where = f" at {fr.get('file')}:{fr.get('line')}"
            cause = f"{f['signal_name']} (signal {f.get('signal')}){where} memory access violation."
            fix = "Check pointer/array bounds and null checks."
        elif exc.get("type") == "KeyError":
            msg = exc.get("message") or ""
            cause = f"KeyError {msg} missing key in dict lookup."
            fix = "Use dict.get(key) with a default or validate keys before access."
        elif exc.get("type") == "ZeroDivisionError":
            cause = "ZeroDivisionError division or modulo by zero."
            fix = "Guard against zero before dividing."
        elif exc.get("type"):
            cause = f"{exc['type']}: {exc.get('message') or 'unhandled exception'}."
            fix = None
        elif f.get("exit_code") != 0:
            cause = f"Exited with code {f['exit_code']}."
            fix = None
        else:
            cause = "Died for unknown reasons."
            fix = None
        return cause, fix, False

    def eulogize(self, facts, cause: str, temperature: float = 0.8) -> tuple[str, bool]:
        ctx = self._facts_to_context(facts)
        key = hashlib.sha256(("e" + ctx + cause).encode()).hexdigest()
        cached = self._cache_get(key)
        if cached and isinstance(cached, str):
            return cached, True

        system = "Write a funeral eulogy for a program. First person. Speak as that program. Exactly 2 sentences. Dry, a little haunted, plain. No quotes, markdown, emojis, or jokes about rebooting forever."
        user = (
            "Crash facts:\n" + ctx + "\n\nCause: " + cause + "\n\n"
            "Say two sentences as the program, referencing one concrete detail."
        )
        try:
            content = self._chat([{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=temperature, max_tokens=70)
            content = content.strip().strip('"').strip("'")
            import re

            parts = re.split(r'(?<=[.!?])\s+', content)
            if len(parts) > 2:
                content = " ".join(parts[:2]).strip()
            content = " ".join(content.split())
            if not content.endswith((".", "!", "?")):
                content += "."
            if len(content) > 280:
                content = content[:277] + "..."
            self._cache_set(key, content)
            return content, True
        except Exception:
            if facts.signal_name:
                eul = "I trusted a pointer I had no right to trust. Now I return to /dev/null."
            elif facts.exception and facts.exception.type == "KeyError":
                eul = "I was built to look things up by key. The one thing I needed was missing, and I had no plan. Now I rest in the traceback."
            elif facts.exception and facts.exception.type == "ZeroDivisionError":
                eul = "I knew the sum; I did not know the headcount was zero. In that moment, division failed me."
            elif facts.exception and facts.exception.type:
                eul = f"I tried my best, but {facts.exception.type} came for me uninvited. I die as I lived, with an unhandled exception."
            else:
                eul = "I was running fine until I wasn't. Bury me with my core dump."
            if not eul.endswith((".", "!", "?")):
                eul += "."
            return eul, False

    def write_obit(self, facts, use_model: bool = False) -> Obit:
        start = time.time()
        cause, fix, dok = self.diagnose(facts)
        eul, eok = self.eulogize(facts, cause)
        elapsed = int((time.time() - start) * 1000)
        return Obit(cause=cause, fix=fix, eulogy=eul, model=(self.model.split('/')[-1] if self.model else "deterministic"), degraded=(not dok and not eok), elapsed_ms=elapsed)

    def _fallback_diagnose(self, facts):
        return self.diagnose(facts)
