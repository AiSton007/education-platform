"""Structured JSON logging built on top of structlog + stdlib logging.

The platform expects every service to emit JSON-formatted logs to stdout containing at least
``service``, ``request_id``, ``level``, ``event``, ``ts`` fields.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

import structlog

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def bind_request_id(request_id: str | None) -> None:
    """Bind the current request id to the contextvar so structlog picks it up."""
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    return _request_id_var.get()


def _request_id_processor(_: object, __: str, event_dict: dict) -> dict:
    rid = _request_id_var.get()
    if rid:
        event_dict.setdefault("request_id", rid)
    return event_dict


def _service_name_processor_factory(service_name: str):
    def _proc(_: object, __: str, event_dict: dict) -> dict:
        event_dict.setdefault("service", service_name)
        return event_dict

    return _proc


def setup_logging(level: str, service_name: str) -> None:
    """Configure structlog + stdlib logging for the whole process.

    Must be called once at startup before any logger is used.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts")
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _service_name_processor_factory(service_name),
        _request_id_processor,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(numeric_level)

    for noisy in ("uvicorn.access", "uvicorn.error", "uvicorn"):
        logging.getLogger(noisy).handlers = [handler]
        logging.getLogger(noisy).propagate = False
        logging.getLogger(noisy).setLevel(numeric_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name) if name else structlog.get_logger()
