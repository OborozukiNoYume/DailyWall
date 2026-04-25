import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
MAX_LOG_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5

_HANDLER_KEY_ATTR = "_dailywall_handler_key"

_COMPONENT_PREFIXES = {
    "api": ("dailywall.api", "uvicorn", "fastapi", "starlette"),
    "crawl": ("dailywall.crawl",),
    "maintenance": ("dailywall.maintenance",),
}

_COMPONENT_FILES = {
    "api": "api.log",
    "crawl": "crawl.log",
    "maintenance": "maintenance.log",
}


class PrefixFilter(logging.Filter):
    def __init__(self, prefixes: tuple[str, ...]):
        super().__init__()
        self.prefixes = prefixes

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith(self.prefixes)


def get_component_logger(component: str, name: str | None = None) -> logging.Logger:
    logger_name = f"dailywall.{component}"
    if name:
        logger_name = f"{logger_name}.{name}"
    return logging.getLogger(logger_name)


def configure_logging(
    component: str, *, log_dir: str, console: bool = True
) -> logging.Logger:
    if component not in _COMPONENT_FILES:
        raise ValueError(f"Unsupported logging component: {component}")

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    component_handler = RotatingFileHandler(
        Path(log_dir) / _COMPONENT_FILES[component],
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    component_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    component_handler.addFilter(PrefixFilter(_COMPONENT_PREFIXES[component]))
    _replace_handler(root_logger, f"{component}:file", component_handler)

    error_handler = RotatingFileHandler(
        Path(log_dir) / "error.log",
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    _replace_handler(root_logger, "shared:error", error_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
        _replace_handler(root_logger, "shared:console", console_handler)
    else:
        _remove_handler(root_logger, "shared:console")

    if component == "api":
        _configure_api_loggers()

    return get_component_logger(component)


def _replace_handler(
    logger: logging.Logger, handler_key: str, new_handler: logging.Handler
) -> None:
    _remove_handler(logger, handler_key)
    setattr(new_handler, _HANDLER_KEY_ATTR, handler_key)
    logger.addHandler(new_handler)


def _remove_handler(logger: logging.Logger, handler_key: str) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_KEY_ATTR, None) == handler_key:
            logger.removeHandler(handler)
            handler.close()


def _configure_api_loggers() -> None:
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
