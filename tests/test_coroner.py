from requiem import coroner, capture

def test_redact_secrets():
    s = 'token=ghp_ABCDEF1234567890 and email test@example.com at /home/james/secret.txt'
    out, c = coroner._redact(s)
    assert "[redacted:key]" in out or "[redacted" in out
    assert "test@example.com" not in out
    assert "/home/[user]" in out

def test_python_traceback():
    stderr = '''Traceback (most recent call last):
  File "examples/lost_config.py", line 14, in load_user
    return config["users"][user_id]
KeyError: 'user_id'
'''
    exc, frames = coroner._extract_python_traceback(stderr)
    assert exc.type == "KeyError"
    assert exc.message == "'user_id'"
    assert frames
    assert frames[-1].line == 14

def test_signal_class():
    class D:
        exit_code = -11
        signal = 11
        signal_name = "SIGSEGV"
        stderr = ""
        stdout = ""
        timed_out = False
        argv = ["./segv"]
    facts = coroner.examine(D())
    assert facts.cause_class == "signal"
    assert facts.signal_name == "SIGSEGV"
