# Requiem

A crash post-mortem that speaks as the program that died.

**Ghost in the Machine** - for the Hacktoberfest 2026 Week 4 DEV Challenge.

## What it does

Run any command under Requiem. When it dies, it:

1. **Captures** how it died (exit code, signal, stderr/stdout, duration).
2. **Coroners** the crash - parses tracebacks, maps signals, reads the failing line from source, and **redacts secrets** (tokens, keys, emails, home paths, IPs) before anything else sees them.
3. **Asks a ghost** - a local open-weight model (Gemma 3 1B via `llama-server`) writes a first-person eulogy and a terse diagnosis. If the model is offline, it falls back to a deterministic obituary.
4. **Buries** it in a local JSONL graveyard (`data/obituaries.jsonl`) and prints an obituary card.

Every crash gets a funeral.

## Why open innovation matters

**stderr is sensitive.** A crash log contains file paths, hostnames, SQL, auth headers, customer data, and sometimes tokens. Pasting it into a cloud "explain my crash" tool ships all of that to a third party. Requiem runs inference on your own machine, and its coroner redacts secrets before the model ever sees them. The eulogy never leaves `127.0.0.1`.

**It works with the lights (and network) off.** The model, prompt, and logic are local files. Swap `gemma-3-1b-it-Q4_K_M.gguf` for any GGUF. Change the prompt. Read the code - it's ~400 lines, all stdlib.

**Open beats opaque.** A hybrid system: code does what code should (parsing, redaction, signal mapping). A local model handles what language needs (voice, eulogy). Both are inspectable and replaceable.

## Demo

```bash
# start a local llama-server with Gemma 3 1B
make llama
# or: make server

# run the demos
make demo
```

```
┌─ REQUIEM ──────────────────────────────────────────────────┐
│ requiem-8f3a21  python3 examples/lost_config.py  112ms     │
│ died of KeyError: 'user_id'                                 │
├─────────────────────────────────────────────────────────────┤
│ WHERE                                                       │
│   examples/lost_config.py:14 in load_user                   │
│     return config["users"][user_id]                         │
│ CAUSE                                                       │
│   KeyError: 'user_id' - looked up a missing key in a dict. │
│ FIX                                                         │
│   Validate input or use .get() with a default.              │
│ EULOGY                                                      │
│   I was only ever asked for keys I had. I never learned to  │
│   say no, and now I say nothing.                             │
│ redacted:0                                                  │
└─────────────────────────────────────────────────────────────┘
```

Segfaults get their due too:

```bash
make examples/segv && PYTHONPATH=. python3 -m requiem run -- ./examples/segv
```

## Quick start

```bash
# Requires a local Gemma GGUF and llama-server (see Makefile)
export REQ_SERVER=http://127.0.0.1:8099
PYTHONPATH=. python3 -m requiem run -- <your-command>
PYTHONPATH=. python3 -m requiem list
PYTHONPATH=. python3 -m requiem show requiem-xxxxxx
```

Run with `--no-model` for a deterministic obituary with no network/model needed.

## Build it yourself

```bash
make models    # check model
make examples/segv
make demo
make test
```

## Project layout

- `requiem/capture.py` - subprocess runner, exit codes/signals
- `requiem/coroner.py` - traceback parse, source read, secret redaction
- `requiem/ghost.py` - local llama-server client, eulogy + diagnosis, cache
- `requiem/store.py` - JSONL graveyard
- `requiem/render.py` - terminal obituary card
- `tests/` - coroner + capture tests (no model required)
- `examples/` - sample crashes for the demo

## License

MIT
