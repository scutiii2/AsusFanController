import logging

from asusfancontrol.logging_setup import setup_logging


def test_setup_logging_writes_to_file(tmp_path):
    path = tmp_path / "sub" / "app.log"
    logger = logging.getLogger("asusfancontrol")
    before = list(logger.handlers)
    try:
        setup_logging(path)
        logging.getLogger("asusfancontrol.test").info("hello")
        for h in logger.handlers:
            h.flush()
        assert "hello" in path.read_text(encoding="utf-8")
    finally:
        for h in list(logger.handlers):
            if h not in before:
                logger.removeHandler(h)
                h.close()


def test_setup_logging_swallows_unwritable_path(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    setup_logging(blocker / "app.log")  # parent is a file: must not raise
