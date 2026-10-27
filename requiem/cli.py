"""CLI for requiem."""

from __future__ import annotations

import json
import os
import sys

from . import capture
from . import coroner
from . import ghost
from . import render
from . import store

def help_text() -> str:
    return """requiem - a crash post-mortem that speaks as the program that died

Usage:
  requiem run -- <command> [args...]  run a command and bury its corpse
  requiem list                      show the graveyard
  requiem show <id>                 inspect a particular obituary
  requiem --version                 print version

Environment:
  REQ_SERVER   llama-server base URL (default: http://127.0.0.1:8099)
  REQ_MODEL    model name/path hint (default: empty)
  REQ_DATA_DIR graveyard directory (default: data)
"""

def main(argv: list[str] | None = None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(help_text())
        return 0

    if argv[0] in ("-h", "--help", "help"):
        print(help_text())
        return 0

    if argv[0] in ("-v", "--version"):
        from . import __version__

        print(__version__)
        return 0

    data_dir = os.environ.get("REQ_DATA_DIR", "data")
    graveyard = store.Graveyard(os.path.join(data_dir, "obituaries.jsonl"))
    g = ghost.Ghost()

    if argv[0] == "list":
        items = graveyard.list(limit=30)
        if not items:
            print("Graveyard empty. Run `requiem run -- <cmd>` to inter a corpse.")
            return 0
        for rec in items:
            d = rec.get("death", {})
            o = rec.get("obit", {})
            print(f"{d.get('id')}  {' '.join(d.get('argv') or [])[:40]:40}  {o.get('cause','')[:40]}")
        return 0

    if argv[0] == "show":
        if len(argv) < 2:
            print("usage: requiem show <id>", file=sys.stderr)
            return 2
        rec = graveyard.get(argv[1])
        if not rec:
            print(f"not found: {argv[1]}", file=sys.stderr)
            return 1
        print(render.Card().show(rec))
        return 0

    if argv[0] == "run":
        rest = argv[1:]
        if rest and rest[0] == "--":
            rest = rest[1:]
        if not rest:
            print("usage: requiem run -- <command> [args...]", file=sys.stderr)
            return 2

        no_model = "--no-model" in rest
        if no_model:
            rest = [x for x in rest if x != "--no-model"]

        timeout = 30.0
        new_rest = []
        i = 0
        while i < len(rest):
            if rest[i] == "--timeout" and i + 1 < len(rest):
                try:
                    timeout = float(rest[i + 1])
                except Exception:
                    pass
                i += 2
                continue
            new_rest.append(rest[i])
            i += 1
        rest = new_rest

        try:
            death = capture.run(rest, timeout=timeout)
        except SystemExit as e:
            print(e, file=sys.stderr)
            return 127

        facts = coroner.examine(death)
        obit = g.write_obit(facts, use_model=not no_model)

        record = {
            "death": death.to_dict(),
            "facts": facts.to_dict(),
            "obit": obit.to_dict(),
        }
        graveyard.bury(record)
        print(render.Card().show(record))
        if facts.redactions:
            print(f"secrets redacted before inference: {facts.redactions}")
        return death.exit_code if death.exit_code >= 0 else 128 - death.exit_code if death.exit_code < 0 else death.exit_code

    print(f"unknown command: {argv[0]}", file=sys.stderr)
    print(help_text(), file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
