import logging
from saveimage_unimeta.defs import formatters


def _reset_mode(monkeypatch, propagate: str):
    monkeypatch.setenv("METADATA_HASH_LOG_PROPAGATE", propagate)
    # Force re-init and sync internal propagate flag
    formatters._LOGGER_INITIALIZED = False  # type: ignore
    # Update internal flag used during initialization
    formatters._HASH_LOG_PROPAGATE = (propagate != "0")  # type: ignore
    # Reset warned sets to allow unresolved log emission each test
    formatters._WARNED_UNRESOLVED.clear()  # type: ignore


def test_hash_log_propagate_off(monkeypatch):
    formatters.set_hash_log_mode("detailed")
    _reset_mode(monkeypatch, "0")
    # Attach spy handler on module logger directly
    logger = logging.getLogger(formatters.__name__)
    received = []
    class Spy(logging.Handler):
        def emit(self, record):
            received.append(record.getMessage())
    spy = Spy()
    logger.addHandler(spy)
    try:
        formatters.calc_model_hash("nonexistent_model_12345", None)
        # Ensure unresolved log present on module logger
        assert any("unresolved model" in m for m in received)
        # We can assert the module logger propagate flag is False
        assert logger.propagate is False
    finally:
        logger.removeHandler(spy)


def test_hash_log_propagate_on(monkeypatch):
    formatters.set_hash_log_mode("detailed")
    _reset_mode(monkeypatch, "1")
    logger = logging.getLogger(formatters.__name__)
    module_received = []
    root_received = []
    class Spy(logging.Handler):
        def emit(self, record):
            module_received.append(record.getMessage())
    class RootSpy(logging.Handler):
        def emit(self, record):  # pragma: no cover - minimal logic
            root_received.append(record.getMessage())
    spy = Spy()
    rspy = RootSpy()
    logger.addHandler(spy)
    logging.getLogger().addHandler(rspy)
    try:
        formatters.calc_model_hash("nonexistent_model_98765", None)
        assert any("unresolved model" in m for m in module_received)
        assert any("unresolved model" in m for m in root_received)
        assert logger.propagate is True
    finally:
        logger.removeHandler(spy)
        logging.getLogger().removeHandler(rspy)
