"""Endpoints for reports."""

from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from pkg.errors import Forbidden, UpstreamError
from pkg.logger import get_logger
from services.report_service.app.deps import (
    CurrentUserDep,
    InternalCallerDep,
    get_reports_service,
)
from services.report_service.app.schemas import (
    RecommendationOut,
    ReportIn,
    ReportOut,
    ReportsList,
)
from services.report_service.app.services.reports import ReportsService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_AUTHORS = {"manager", "admin"}
_log = get_logger("report-service.routes")

_template_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).resolve().parent.parent / "templates")),
    autoescape=select_autoescape(["html", "j2"]),
)


@router.post(
    "",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_report(
    payload: ReportIn,
    _: InternalCallerDep,
    service: Annotated[ReportsService, Depends(get_reports_service)],
) -> ReportOut:
    data = payload.model_dump(mode="json")
    report = await service.create(
        attempt_id=payload.attempt_id,
        user_id=payload.user_id,
        analysis_id=payload.analysis_id,
        score=payload.score,
        data=data,
        recommendations=[r.model_dump(mode="json") for r in payload.recommendations],
    )
    return _serialize(report)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[ReportsService, Depends(get_reports_service)],
) -> ReportOut:
    report = await service.get(report_id)
    if user.role not in _AUTHORS and str(report.user_id) != user.id:
        raise Forbidden("Cannot view foreign report")
    return _serialize(report)


@router.get("/user/{user_id}", response_model=ReportsList)
async def list_reports(
    user_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[ReportsService, Depends(get_reports_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ReportsList:
    if user.role not in _AUTHORS and str(user_id) != user.id:
        raise Forbidden("Cannot list foreign reports")
    items, total = await service.list_by_user(user_id, limit=limit, offset=offset)
    return ReportsList(items=[_serialize(r) for r in items], total=total)


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[ReportsService, Depends(get_reports_service)],
    format: Literal["json", "html", "pdf"] = Query(default="pdf"),
) -> Response:
    report = await service.get(report_id)
    if format == "pdf" and user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can download PDF reports")
    if user.role not in _AUTHORS and str(report.user_id) != user.id:
        raise Forbidden("Cannot download foreign report")

    if format == "json":
        body = json.dumps(_serialize(report).model_dump(mode="json"), ensure_ascii=False, indent=2)
        return JSONResponse(
            content=json.loads(body),
            headers={"Content-Disposition": f'attachment; filename="report-{report.id}.json"'},
        )

    html = _render_report_html(report)

    if format == "html":
        return HTMLResponse(
            content=html,
            headers={"Content-Disposition": f'attachment; filename="report-{report.id}.html"'},
        )

    try:
        from xhtml2pdf import pisa
    except Exception as exc:
        _log.error("pdf_backend_unavailable", report_id=str(report.id), err=str(exc))
        raise UpstreamError("PDF backend is not available in current environment") from exc

    pdf_buffer = io.BytesIO()
    status_code = pisa.CreatePDF(src=io.StringIO(html), dest=pdf_buffer, encoding="utf-8")
    if status_code.err:
        _log.error("pdf_render_failed", report_id=str(report.id))
        raise UpstreamError("Failed to render PDF report")

    pdf_bytes = pdf_buffer.getvalue()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.pdf"'},
    )


def _render_report_html(report) -> str:
    data = report.data or {}
    test = data.get("test") or {}
    participant = data.get("participant") or {}
    items = data.get("items") or []
    recommendations = data.get("recommendations") or [
        {
            "topic": r.topic,
            "reason": r.reason,
            "resource_url": r.resource_url,
        }
        for r in report.recommendations
    ]
    template = _template_env.get_template("report.html.j2")
    return template.render(
        report=report,
        test=test,
        participant=participant,
        items=items,
        recommendations=recommendations,
    )


def _serialize(report) -> ReportOut:
    return ReportOut(
        id=report.id,
        attempt_id=report.attempt_id,
        user_id=report.user_id,
        analysis_id=report.analysis_id,
        score=float(report.score),
        data=report.data,
        created_at=report.created_at,
        recommendations=[
            RecommendationOut(id=r.id, topic=r.topic, resource_url=r.resource_url, reason=r.reason)
            for r in report.recommendations
        ],
    )
