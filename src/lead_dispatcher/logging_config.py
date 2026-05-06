from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from .settings import settings
from .utils import mask_phone_numbers


class PhoneMaskingFilter(logging.Filter):
    @staticmethod
    def _mask_value(value):
        if isinstance(value, str):
            return mask_phone_numbers(value)

        return value

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_phone_numbers(str(record.msg))

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: self._mask_value(value)
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(self._mask_value(value) for value in record.args)

        return True


def setup_logging() -> None:
    log_dir = Path(getattr(settings, "log_dir", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level_name = getattr(settings, "log_level", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    retention_days = int(getattr(settings, "log_retention_days", 7))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "dispatcher.log",
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    if getattr(settings, "log_mask_phone", True):
        phone_masking_filter = PhoneMaskingFilter()
        file_handler.addFilter(phone_masking_filter)
        console_handler.addFilter(phone_masking_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
