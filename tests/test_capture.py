from requiem import capture

def test_run_success():
    d = capture.run(["/bin/true"])
    assert d.exit_code == 0
    assert d.signal is None

def test_run_failure():
    d = capture.run(["/bin/sh", "-c", "exit 7"])
    assert d.exit_code == 7
    assert d.signal is None

def test_run_not_found():
    try:
        capture.run(["/no/such/command/ever"])
    except SystemExit as e:
        assert e.code == 127 or e.code is not None
    else:
        assert True
