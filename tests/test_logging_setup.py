"""Unit tests for logging_setup (JOB-E done-when: 'a unit test asserts the logger emits
at the expected level')."""
import io
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from mamey import logging_setup


def _capture(level_env=None, msg_level="info"):
    """v9.7.407: MAMEY_LOG is now restored. It used to be set and left set, so whichever level the
    last test happened to pass leaked into every subsequent test in the process and could change
    their logging behaviour. Restored in a finally so an assertion failure cannot skip it."""
    import os
    buf = io.StringIO()
    previous = os.environ.get("MAMEY_LOG")
    try:
        if level_env is not None:
            os.environ["MAMEY_LOG"] = level_env
        logging_setup.configure(stream=buf)
        log = logging_setup.get_logger("test_mod")
        getattr(log, msg_level)("hello [test]")
        return buf.getvalue()
    finally:
        if previous is None:
            os.environ.pop("MAMEY_LOG", None)
        else:
            os.environ["MAMEY_LOG"] = previous


def test_info_emits_bare_message_at_default():
    assert _capture(level_env="info", msg_level="info") == "hello [test]\n"


def test_debug_suppressed_at_default_info():
    assert _capture(level_env="info", msg_level="debug") == ""


def test_debug_emits_when_env_lowered():
    assert _capture(level_env="debug", msg_level="debug") == "hello [test]\n"


def test_warning_emits_same_stream_same_bytes():
    assert _capture(level_env="info", msg_level="warning") == "hello [test]\n"


def test_configure_is_idempotent_no_duplicate_lines():
    buf = io.StringIO()
    logging_setup.configure(stream=buf)
    logging_setup.configure(stream=buf)
    logging_setup.get_logger("test_mod2").info("once")
    assert buf.getvalue() == "once\n"
