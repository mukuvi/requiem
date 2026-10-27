"""Render obituaries to the terminal."""

from __future__ import annotations

class Card:
    def __init__(self, width: int = 64):
        self.w = width

    def _hr(self, ch="─"):
        return "┌" + ch * (self.w - 2) + "┐"

    def _mid(self, ch="─"):
        return "├" + ch * (self.w - 2) + "┤"

    def _bot(self, ch="─"):
        return "└" + ch * (self.w - 2) + "┘"

    def _line(self, text: str):
        text = str(text)
        if len(text) >= self.w - 4:
            text = text[: self.w - 7] + "..."
        return "│ " + text.ljust(self.w - 4) + " │"

    def _wrap(self, text: str, indent: str = "  "):
        words = str(text).split()
        out = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 > self.w - 4 - len(indent):
                if cur:
                    out.append(indent + cur)
                    cur = ""
                while len(w) > self.w - 4 - len(indent):
                    out.append(indent + w[: self.w - 4 - len(indent) - 3] + "...")
                    w = w[self.w - 4 - len(indent) - 3 :]
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            out.append(indent + cur)
        return out

    def show(self, record: dict) -> str:
        death = record.get("death", {})
        facts = record.get("facts", {})
        obit = record.get("obit", {})
        lines = []
        lines.append("┌─ R E Q U I E M ─" + "─" * (self.w - 18) + "┐")
        header = f"{death.get('id','?')}    {' '.join(death.get('argv') or [])[:28]}    {death.get('duration_ms')}ms"
        lines.append("│ " + header.ljust(self.w - 4) + " │")
        exc = facts.get("exception") or {}
        died = obit.get("cause") or exc.get("type") or death.get("signal_name") or f"exit {death.get('exit_code')}"
        lines.append("│ " + ("died of " + died).ljust(self.w - 4) + " │")
        lines.append("├────────────────────────────────────────────────────────┤")
        lines.append("│  LAST WORDS                                             │")
        for l in self._wrap(facts.get("last_words") or "", indent="  "):
            lines.append("│" + l.ljust(self.w - 1) + "│" if False else "│ " + l[2:].ljust(self.w - 4) if l.startswith("  ") else "│ " + l.ljust(self.w - 4))
        lines = []
        lines.append("┌─ REQUIEM ─" + "─" * (self.w - 12) + "┐")
        top = f"{death.get('id','?')}  {' '.join(death.get('argv') or [])[:34]}  {death.get('duration_ms')}ms"
        lines.append(self._line(top))
        sub = f"died of {died}"
        lines.append(self._line(sub))
        lines.append("├" + "─" * (self.w - 2) + "┤")
        lines.append(self._line("WHERE"))
        frs = facts.get("frames") or []
        if frs:
            fr = frs[-1]
            where = f"  {fr.get('file')}:{fr.get('line')} in {fr.get('function')}"
            lines.append(self._line(where[: self.w - 4]))
            if fr.get("source"):
                lines.append(self._line(f"    {fr['source']}"[: self.w - 4]))
        else:
            if death.get("signal_name"):
                lines.append(self._line(f"  killed by {death.get('signal_name')}"))
            else:
                lines.append(self._line(f"  exit code {death.get('exit_code')}"))

        lines.append(self._line("CAUSE"))
        for l in self._wrap(obit.get("cause") or "", indent="  "):
            lines.append("│ " + l.ljust(self.w - 4) + " │")
        if obit.get("fix"):
            lines.append(self._line("FIX"))
            for l in self._wrap(obit.get("fix"), indent="  "):
                lines.append("│ " + l.ljust(self.w - 4) + " │")
        lines.append(self._line("EULOGY"))
        for l in self._wrap(obit.get("eulogy") or "", indent="  "):
            lines.append("│ " + l.ljust(self.w - 4) + " │")
        meta = []
        if facts.get("redactions"):
            meta.append(f"redacted:{facts['redactions']}")
        if obit.get("degraded"):
            meta.append("model:degraded")
        elif obit.get("model"):
            meta.append(f"model:{obit['model'].split('/')[-1][:20]}")
        lines.append(self._line(" ".join(meta) or " "))
        lines.append("└" + "─" * (self.w - 2) + "┘")
        return "\n".join(lines)
