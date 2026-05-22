"""Prometheus metrics integration.

Uses ``prometheus-fastapi-instrumentator`` for HTTP RED metrics (request count, latency,
errors) plus a tiny registry helper for business metrics.
"""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator


def instrument(app: FastAPI, service_name: str) -> Instrumentator:
    """Attach default RED metrics + expose ``/metrics``."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        inprogress_name="http_requests_in_progress",
        inprogress_labels=True,
    ).add(_default_request_counter(service_name))
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return instrumentator


def _default_request_counter(service_name: str):
    """Custom counter that includes the service name as a label."""
    counter = Counter(
        "service_http_requests_total",
        "HTTP requests by service",
        ("service", "method", "handler", "status"),
    )

    def _instrumentation(info) -> None:
        counter.labels(
            service=service_name,
            method=info.request.method,
            handler=info.modified_handler,
            status=info.modified_status,
        ).inc()

    return _instrumentation


# Business metrics ------------------------------------------------------------------------------

business_events = Counter(
    "business_events_total",
    "Business events emitted by services",
    ("service", "event"),
)

business_latency = Histogram(
    "business_event_duration_seconds",
    "Latency of selected business operations",
    ("service", "event"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
