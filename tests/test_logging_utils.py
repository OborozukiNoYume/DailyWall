import logging
from pathlib import Path

from app import logging_utils


def _clear_managed_handlers():
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, logging_utils._HANDLER_KEY_ATTR, None):
            root_logger.removeHandler(handler)
            handler.close()


def _flush_managed_handlers():
    for handler in logging.getLogger().handlers:
        if getattr(handler, logging_utils._HANDLER_KEY_ATTR, None):
            handler.flush()


def test_configure_logging_routes_component_and_error_logs(tmp_path):
    _clear_managed_handlers()

    logging_utils.configure_logging(
        "maintenance", log_dir=str(tmp_path), console=False
    )
    logger = logging_utils.get_component_logger("maintenance", "tests")

    logger.info("maintenance info")
    logger.error("maintenance error")
    _flush_managed_handlers()

    maintenance_log = Path(tmp_path / "maintenance.log").read_text(
        encoding="utf-8"
    )
    error_log = Path(tmp_path / "error.log").read_text(encoding="utf-8")

    assert "maintenance info" in maintenance_log
    assert "maintenance error" in maintenance_log
    assert "maintenance info" not in error_log
    assert "maintenance error" in error_log


def test_configure_logging_for_api_resets_uvicorn_handlers(tmp_path):
    _clear_managed_handlers()
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.addHandler(logging.NullHandler())
    uvicorn_logger.propagate = False

    logging_utils.configure_logging("api", log_dir=str(tmp_path), console=False)

    assert uvicorn_logger.handlers == []
    assert uvicorn_logger.propagate is True
