# ruff: noqa: RUF001, E501
"""
Generate diploma presentation PDF.

Usage:
    uv run python scripts/generate_presentation.py

Output:
    docs/diploma-presentation.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas

# ─── Page geometry ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = landscape(A4)   # 841.89 x 595.28 pt
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
CONTENT_H = PAGE_H - 2 * MARGIN

# ─── Palette ───────────────────────────────────────────────────────────────────
C_BG      = colors.white
C_HEADER  = colors.HexColor("#1E3A5F")   # dark blue header bar
C_ACCENT  = colors.HexColor("#2563EB")   # accent blue
C_TEXT    = colors.HexColor("#0F172A")   # near-black
C_SEC     = colors.HexColor("#475569")   # secondary text
C_FILL    = colors.HexColor("#F1F5F9")   # light grey fill
C_BORDER  = colors.HexColor("#CBD5E1")   # border
C_SUCCESS = colors.HexColor("#166534")
C_WARN    = colors.HexColor("#92400E")
C_DANGER  = colors.HexColor("#991B1B")
C_MUTED   = colors.HexColor("#64748B")

# ─── Font registration ─────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    # (regular_path, bold_path, reg_name, bold_name)
    (r"C:\Windows\Fonts\DejaVuSans.ttf",    r"C:\Windows\Fonts\DejaVuSans-Bold.ttf",    "DejaVuSans",    "DejaVuSans-Bold"),
    (r"C:\Windows\Fonts\arial.ttf",          r"C:\Windows\Fonts\arialbd.ttf",             "Arial",         "Arial-Bold"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  "DejaVuSans", "DejaVuSans-Bold"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf",           "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",           "DejaVuSans", "DejaVuSans-Bold"),
]

FONT_REGULAR = "DejaVuSans"
FONT_BOLD    = "DejaVuSans-Bold"

def _register_fonts() -> bool:
    global FONT_REGULAR, FONT_BOLD
    for reg_path, bold_path, reg_name, bold_name in FONT_CANDIDATES:
        if Path(reg_path).exists() and Path(bold_path).exists():
            pdfmetrics.registerFont(TTFont(reg_name,  reg_path))
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            FONT_REGULAR = reg_name
            FONT_BOLD    = bold_name
            print(f"[fonts] loaded '{reg_name}' from {reg_path}")
            return True
    print("[fonts] no Cyrillic font found — using Helvetica (Cyrillic may not render)")
    FONT_REGULAR = "Helvetica"
    FONT_BOLD    = "Helvetica-Bold"
    return False

# ─── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_slide_chrome(c: pdf_canvas.Canvas, title: str, slide_n: int, total: int) -> None:
    """Header bar + slide number footer."""
    # Background
    c.setFillColor(C_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Header bar
    c.setFillColor(C_HEADER)
    c.rect(0, PAGE_H - 28 * mm, PAGE_W, 28 * mm, fill=1, stroke=0)

    # Title
    c.setFont(FONT_BOLD, 18)
    c.setFillColor(colors.white)
    c.drawString(MARGIN, PAGE_H - 16 * mm, title)

    # Slide number (right-aligned in header)
    num_txt = f"{slide_n} / {total}"
    c.setFont(FONT_REGULAR, 11)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 16 * mm, num_txt)

    # Bottom line
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.5)
    c.line(MARGIN, 8 * mm, PAGE_W - MARGIN, 8 * mm)

    # Slide mini-dots
    dot_x = MARGIN
    for i in range(total):
        c.setFillColor(C_ACCENT if i == slide_n - 1 else C_BORDER)
        c.circle(dot_x + i * 5 * mm, 5 * mm, 1.5 * mm, fill=1, stroke=0)


def _text(c: pdf_canvas.Canvas, x: float, y: float, text: str,
          font=None, size: float = 11, color=None, align: str = "left") -> None:
    c.setFont(font or FONT_REGULAR, size)
    c.setFillColor(color or C_TEXT)
    if align == "right":
        c.drawRightString(x, y, text)
    elif align == "center":
        c.drawCentredString(x, y, text)
    else:
        c.drawString(x, y, text)


def _box(c: pdf_canvas.Canvas, x: float, y: float, w: float, h: float,
         title: str = "", lines: list[str] | None = None,
         accent: bool = False, fill_color=None) -> None:
    """Draws a card-like box with optional title and bullet lines."""
    fc = fill_color or C_FILL
    c.setFillColor(fc)
    c.setStrokeColor(C_ACCENT if accent else C_BORDER)
    c.setLineWidth(1 if accent else 0.5)
    c.roundRect(x, y, w, h, 2 * mm, fill=1, stroke=1)
    ty = y + h - 6 * mm
    if title:
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(C_ACCENT if accent else C_TEXT)
        c.drawString(x + 3 * mm, ty, title)
        ty -= 5 * mm
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.3)
        c.line(x + 2 * mm, ty + 2.5 * mm, x + w - 2 * mm, ty + 2.5 * mm)
        ty -= 1 * mm
    if lines:
        c.setFont(FONT_REGULAR, 8)
        c.setFillColor(C_TEXT)
        for line in lines:
            if ty < y + 2 * mm:
                break
            c.drawString(x + 3 * mm, ty, line)
            ty -= 4.5 * mm


def _pill(c: pdf_canvas.Canvas, x: float, y: float, text: str,
          tone: str = "neutral") -> None:
    tone_map = {
        "success": (colors.HexColor("#DCFCE7"), C_SUCCESS),
        "warn":    (colors.HexColor("#FEF3C7"), C_WARN),
        "danger":  (colors.HexColor("#FEE2E2"), C_DANGER),
        "info":    (colors.HexColor("#DBEAFE"), C_ACCENT),
        "neutral": (C_FILL, C_MUTED),
    }
    bg, fg = tone_map.get(tone, tone_map["neutral"])
    w = len(text) * 4.5 + 8
    c.setFillColor(bg)
    c.setStrokeColor(fg)
    c.setLineWidth(0.5)
    c.roundRect(x, y - 3 * mm, w, 5 * mm, 2 * mm, fill=1, stroke=1)
    c.setFont(FONT_REGULAR, 7)
    c.setFillColor(fg)
    c.drawCentredString(x + w / 2, y, text)


def _svg_box(c, x, y, w, h, label, sub=None, accent=False):
    c.setFillColor(C_FILL)
    c.setStrokeColor(C_ACCENT if accent else C_BORDER)
    c.setLineWidth(1 if accent else 0.5)
    c.roundRect(x, y, w, h, 1.5 * mm, fill=1, stroke=1)
    mid = y + h / 2 + (2 * mm if sub else 0)
    c.setFont(FONT_BOLD if accent else FONT_REGULAR, 8)
    c.setFillColor(C_ACCENT if accent else C_TEXT)
    c.drawCentredString(x + w / 2, mid, label)
    if sub:
        c.setFont(FONT_REGULAR, 7)
        c.setFillColor(C_MUTED)
        c.drawCentredString(x + w / 2, y + h / 2 - 3 * mm, sub)


def _arrow(c, x1, y1, x2, y2):
    import math
    c.setStrokeColor(C_MUTED)
    c.setLineWidth(0.7)
    c.line(x1, y1, x2, y2)
    dx, dy = x2 - x1, y2 - y1
    length = math.sqrt(dx * dx + dy * dy) or 1
    ux, uy = dx / length, dy / length
    ax, ay = x2 - ux * 4 * mm, y2 - uy * 4 * mm
    c.setFillColor(C_MUTED)
    c.setStrokeColor(C_MUTED)
    pts = [
        (x2, y2),
        (ax - uy * 2 * mm, ay + ux * 2 * mm),
        (ax + uy * 2 * mm, ay - ux * 2 * mm),
    ]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def _simple_table(c, x, y, headers, rows,
                  col_widths=None, row_height=6 * mm) -> float:
    """Draws a simple table, returns bottom y."""
    if col_widths is None:
        n = len(headers)
        col_widths = [CONTENT_W / n] * n
    total_w = sum(col_widths)

    # Header row
    hdr_h = 7 * mm
    c.setFillColor(C_HEADER)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.3)
    c.rect(x, y - hdr_h, total_w, hdr_h, fill=1, stroke=1)
    cx = x
    for i, h in enumerate(headers):
        c.setFont(FONT_BOLD, 8)
        c.setFillColor(colors.white)
        c.drawString(cx + 2 * mm, y - hdr_h + 2 * mm, str(h))
        cx += col_widths[i]

    cy = y - hdr_h
    for ri, row in enumerate(rows):
        bg = C_FILL if ri % 2 == 0 else C_BG
        c.setFillColor(bg)
        c.setStrokeColor(C_BORDER)
        c.rect(x, cy - row_height, total_w, row_height, fill=1, stroke=1)
        cx2 = x
        for i, cell in enumerate(row):
            c.setFont(FONT_REGULAR, 7.5)
            c.setFillColor(C_TEXT)
            txt = str(cell)[:55]
            c.drawString(cx2 + 2 * mm, cy - row_height + 2 * mm, txt)
            cx2 += col_widths[i]
        cy -= row_height
    return cy


def _stat_strip(c, x, y, stats):
    """stats: list of (value, label) tuples."""
    sw = CONTENT_W / len(stats)
    for i, (val, lbl) in enumerate(stats):
        sx = x + i * sw
        c.setFillColor(C_FILL)
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.5)
        c.roundRect(sx + 2 * mm, y - 16 * mm, sw - 4 * mm, 16 * mm, 2 * mm, fill=1, stroke=1)
        c.setFont(FONT_BOLD, 16)
        c.setFillColor(C_ACCENT)
        c.drawCentredString(sx + sw / 2, y - 7 * mm, str(val))
        c.setFont(FONT_REGULAR, 8)
        c.setFillColor(C_SEC)
        c.drawCentredString(sx + sw / 2, y - 13 * mm, lbl)


def _start_content(slide_h_used: float = 32 * mm) -> float:
    """Returns starting y for content (below header)."""
    return PAGE_H - slide_h_used


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDES
# ═══════════════════════════════════════════════════════════════════════════════

def slide_01_title(c, n, total):
    _draw_slide_chrome(c, "Микросервисная платформа обучения и тестирования сотрудников", n, total)
    y = PAGE_H - 34 * mm
    _text(c, MARGIN, y, "ДИПЛОМНАЯ РАБОТА", font=FONT_BOLD, size=9, color=C_MUTED)
    y -= 8 * mm
    _text(c, MARGIN, y, "Проектирование, разработка и развёртывание в self-hosted Kubernetes", size=12, color=C_SEC)
    y -= 14 * mm
    _stat_strip(c, MARGIN, y, [
        ("6",      "Микросервисов"),
        ("4",      "K8s нод"),
        ("1",      "LLM интеграция"),
        ("3",      "Роли: employee / manager / admin"),
    ])
    y -= 26 * mm
    bw = (CONTENT_W - 6 * mm) / 3
    for i, (title, lines) in enumerate([
        ("Backend", ["Python 3.12 + FastAPI", "SQLAlchemy 2.0 async + asyncpg", "Alembic, PyJWT, structlog, uv"]),
        ("Frontend", ["React 18 + Vite + TypeScript", "axios, Guard HOC (RBAC)", "nginx-unprivileged"]),
        ("Инфраструктура", ["Kubernetes + Helm + ArgoCD", "Jenkins + Kaniko + Harbor", "PostgreSQL 15 (Bitnami)"]),
    ]):
        _box(c, MARGIN + i * (bw + 3 * mm), y - 22 * mm, bw, 22 * mm,
             title=title, lines=lines, accent=(i == 0))


def slide_02_goals(c, n, total):
    _draw_slide_chrome(c, "Цель и задачи", n, total)
    y = _start_content()
    y -= 3 * mm

    # Left column: problem + scenario
    lw = CONTENT_W * 0.42
    _box(c, MARGIN, y - 30 * mm, lw, 30 * mm,
         title="Проблема",
         lines=[
             "Отсутствие автоматизированного инструмента",
             "тестирования сотрудников с LLM-анализом",
             "слабых мест и персональными рекомендациями.",
         ], accent=True)
    y -= 34 * mm
    _box(c, MARGIN, y - 30 * mm, lw, 30 * mm,
         title="Целевой сценарий",
         lines=[
             "1. Сотрудник проходит тест через браузер",
             "2. LLM-сервис анализирует ответы",
             "3. Report-сервис генерирует PDF/HTML отчёт",
             "4. Руководитель изучает рекомендации",
         ])

    # Right column: task table
    rx = MARGIN + lw + 6 * mm
    rw = CONTENT_W - lw - 6 * mm
    _text(c, rx, PAGE_H - 34 * mm, "Выполненные задачи", font=FONT_BOLD, size=10)
    tasks = [
        ("Микросервисная архитектура (6 сервисов)", "Готово"),
        ("REST API + JWT + Internal JWT", "Готово"),
        ("LLM-интеграция GigaChat / mock", "Готово"),
        ("PDF-отчёты с кириллицей", "Готово"),
        ("Kubernetes + Helm деплой", "Готово"),
        ("CI/CD: Jenkins + Kaniko + ArgoCD", "Готово"),
        ("React SPA с RBAC", "Готово"),
        ("NetworkPolicy: default-deny", "Готово"),
    ]
    ty = PAGE_H - 40 * mm
    for task, status in tasks:
        c.setFont(FONT_REGULAR, 8)
        c.setFillColor(C_TEXT)
        c.drawString(rx, ty, f"• {task}")
        _pill(c, rx + rw - 22 * mm, ty + 1 * mm, status, tone="success")
        ty -= 6 * mm


def slide_03_infra(c, n, total):
    _draw_slide_chrome(c, "Инфраструктура Kubernetes-кластера", n, total)
    y = _start_content() - 3 * mm
    lw = CONTENT_W * 0.48
    rw = CONTENT_W - lw - 6 * mm
    rx = MARGIN + lw + 6 * mm

    # SVG topology
    _text(c, MARGIN, y, "Топология кластера", font=FONT_BOLD, size=10)
    y -= 6 * mm

    bw, bh = 44 * mm, 10 * mm
    cx_center = MARGIN + lw / 2

    # Windows Host
    _svg_box(c, cx_center - bw / 2, y - bh, bw, bh, "Windows Host", "IDE / Git / Lens / kubectl")
    # Line down
    c.setStrokeColor(C_BORDER)
    c.line(cx_center, y - bh, cx_center, y - bh - 8 * mm)
    c.setFont(FONT_REGULAR, 7)
    c.setFillColor(C_MUTED)
    c.drawCentredString(cx_center + 10 * mm, y - bh - 5 * mm, "LAN 192.168.1.0/24")

    # DNS/NFS
    dns_y = y - bh - 8 * mm
    _svg_box(c, MARGIN + 8 * mm, dns_y - bh, lw - 16 * mm, bh,
             "DNS / NFS / Ansible  192.168.1.170",
             "bind9 + nfs-kernel-server + ansible", accent=True)

    # Lines to nodes
    node_y = dns_y - bh - 8 * mm
    node_xs = [MARGIN + 4 * mm, MARGIN + 18 * mm, MARGIN + 32 * mm, MARGIN + 46 * mm]
    node_w, node_h = 13 * mm, 10 * mm
    node_labels = [("control1", ".171"), ("worker1", ".174"), ("worker2", ".175"), ("worker3", ".176")]
    dns_mid_x = MARGIN + 8 * mm + (lw - 16 * mm) / 2
    for i, (nx, (lbl, sub)) in enumerate(zip(node_xs, node_labels, strict=True)):
        mid_x = nx + node_w / 2
        c.setStrokeColor(C_BORDER)
        c.line(dns_mid_x if i == 0 else dns_mid_x + (i - 1.5) * 14 * mm,
               dns_y - bh, mid_x, node_y + node_h)
        _svg_box(c, nx, node_y, node_w, node_h, lbl, sub, accent=(i == 0))

    c.setFont(FONT_REGULAR, 7)
    c.setFillColor(C_MUTED)
    c.drawCentredString(MARGIN + lw / 2, node_y - 4 * mm,
                        "kubeadm · containerd · Calico IPIPCrossSubnet · CoreDNS")

    # Right: component table
    _text(c, rx, PAGE_H - 34 * mm, "Компоненты платформы", font=FONT_BOLD, size=10)
    components = [
        ("kubeadm", "Bootstrap кластера"),
        ("containerd", "Container runtime"),
        ("Calico", "CNI + NetworkPolicy"),
        ("CoreDNS + NodeLocalDNS", "Кластерный DNS"),
        ("MetalLB", "LoadBalancer IP"),
        ("ingress-nginx", "HTTP/HTTPS Ingress"),
        ("cert-manager", "TLS сертификаты"),
        ("nfs-subdir", "StorageClass nfs-client"),
        ("Harbor", "Container Registry"),
        ("ArgoCD", "GitOps CD"),
        ("Jenkins", "CI Pipeline"),
    ]
    _simple_table(c, rx, PAGE_H - 38 * mm,
                  ["Компонент", "Роль"],
                  components,
                  col_widths=[rw * 0.48, rw * 0.52])


def slide_04_arch(c, n, total):
    _draw_slide_chrome(c, "Архитектура приложения", n, total)
    y = _start_content() - 3 * mm
    lw = CONTENT_W * 0.50
    rw = CONTENT_W - lw - 6 * mm
    rx = MARGIN + lw + 6 * mm

    _text(c, MARGIN, y, "Контекстная диаграмма", font=FONT_BOLD, size=10)
    _text(c, rx, y, "Монорепозиторий и принципы", font=FONT_BOLD, size=10)
    y -= 6 * mm

    # Users
    uw, uh = 22 * mm, 8 * mm
    for i, role in enumerate(["Employee", "Manager", "Admin"]):
        uy = y - i * (uh + 2 * mm) - uh
        _svg_box(c, MARGIN, uy, uw, uh, role)

    # Frontend
    fw, fh = 24 * mm, 12 * mm
    fy = y - 1.5 * (uh + 2 * mm) - fh / 2 - uh
    _svg_box(c, MARGIN + uw + 8 * mm, fy, fw, fh, "Frontend", "React SPA")
    # Arrows users -> frontend
    for i in range(3):
        _arrow(c, MARGIN + uw, y - i * (uh + 2 * mm) - uh / 2,
               MARGIN + uw + 8 * mm, fy + fh / 2)

    # Gateway
    gw_x = MARGIN + uw + fw + 10 * mm
    gw_w, gw_h = 28 * mm, 14 * mm
    gy = y - 1.5 * (uh + 2 * mm) - gw_h / 2 - uh
    _svg_box(c, gw_x, gy, gw_w, gw_h, "API Gateway", ":8080", accent=True)
    _arrow(c, MARGIN + uw + fw + 8 * mm, fy + fh / 2, gw_x, gy + gw_h / 2)

    # Services
    svc_x = gw_x + gw_w + 8 * mm
    svc_names = ["auth-service", "user-service", "test-service", "llm-service", "report-service"]
    svc_h = 8 * mm
    for i, svc in enumerate(svc_names):
        sy = y - i * (svc_h + 2 * mm) - svc_h
        _svg_box(c, svc_x, sy, 32 * mm, svc_h, svc, accent=(svc == "test-service"))
        _arrow(c, gw_x + gw_w, gy + gw_h / 2, svc_x, sy + svc_h / 2)

    c.setFont(FONT_REGULAR, 7)
    c.setFillColor(C_MUTED)
    c.drawCentredString(MARGIN + lw / 2, y - 56 * mm, "Все сервисы → PostgreSQL (schema-per-service)")

    # Right column
    monorepo_items = [
        ("pkg/", "config, logger, errors, jwt, db, metrics, health"),
        ("services/", "6 backend-сервисов"),
        ("frontend/", "React + Vite"),
        ("deploy/", "Helm charts + ArgoCD manifests"),
    ]
    ty = PAGE_H - 42 * mm
    for folder, desc in monorepo_items:
        _box(c, rx, ty - 12 * mm, rw, 12 * mm,
             title=folder, lines=[desc])
        ty -= 14 * mm
    ty -= 3 * mm
    principles = [
        "• Один pyproject.toml, uv — менеджер зависимостей",
        "• Per-service extras в optional-dependencies",
        "• 12-factor: конфиг через env, логи в stdout JSON",
        "• Stateless сервисы — данные только в PostgreSQL",
        "• Non-root контейнеры, readOnlyRootFilesystem",
    ]
    for p in principles:
        c.setFont(FONT_REGULAR, 8)
        c.setFillColor(C_TEXT)
        c.drawString(rx, ty, p)
        ty -= 5 * mm


def slide_05_services(c, n, total):
    _draw_slide_chrome(c, "Сервисы платформы", n, total)
    y = _start_content() - 3 * mm
    _simple_table(c, MARGIN, y,
                  ["Сервис", "Порт", "Схема БД", "Ответственность"],
                  [
                      ("api-gateway",    "8080", "—",       "JWT-валидация, проксирование, централизованный формат ошибок"),
                      ("auth-service",   "8080", "auth",    "Регистрация, логин, refresh-токены, bcrypt хэширование"),
                      ("user-service",   "8080", "users",   "Профили, роли, отделы, должности сотрудников"),
                      ("test-service",   "8080", "tests",   "Тесты, вопросы, назначения, попытки — оркестратор submit-flow"),
                      ("llm-service",    "8080", "llm",     "Анализ ответов: GigaChat (prod) / mock (dev)"),
                      ("report-service", "8080", "reports", "Генерация PDF/HTML отчётов (xhtml2pdf + ReportLab)"),
                      ("frontend",       "8080", "—",       "React SPA на nginx-unprivileged, VITE_API_URL → api-gateway"),
                  ],
                  col_widths=[30 * mm, 15 * mm, 20 * mm, CONTENT_W - 65 * mm])
    y -= 80 * mm
    bw = (CONTENT_W - 6 * mm) / 3
    _box(c, MARGIN, y - 22 * mm, bw, 22 * mm,
         title="Healthcheck endpoints",
         lines=["GET /healthz — liveness (процесс жив)",
                "GET /readyz — readiness (БД доступна)",
                "GET /metrics — Prometheus-метрики",
                "GET /docs   — Swagger UI"])
    _box(c, MARGIN + bw + 3 * mm, y - 22 * mm, bw, 22 * mm,
         title="Internal JWT (service-to-service)",
         lines=["Header: X-Internal-Token",
                "HS256, TTL 300 секунд",
                "Проверка iss / aud / exp",
                "Отдельный секрет от пользовательского JWT"])
    _box(c, MARGIN + 2 * (bw + 3 * mm), y - 22 * mm, bw, 22 * mm,
         title="Миграции (Alembic)",
         lines=["Per-service миграции",
                "K8s Job (PreSync hook)",
                "ArgoCD sync-wave -10",
                "Сервисы стартуют после migrate"])


def slide_06_stack(c, n, total):
    _draw_slide_chrome(c, "Технологический стек", n, total)
    y = _start_content() - 3 * mm
    hw = (CONTENT_W - 5 * mm) / 2

    _simple_table(c, MARGIN, y,
                  ["Слой", "Технология", "Роль"],
                  [
                      ("Runtime",     "Python 3.12",            "Язык бэкенда"),
                      ("Web",         "FastAPI + Uvicorn",       "ASGI-фреймворк"),
                      ("ORM",         "SQLAlchemy 2.0 async",   "Async ORM"),
                      ("DB driver",   "asyncpg",                 "Async PostgreSQL"),
                      ("Migrations",  "Alembic",                 "Версионирование схемы"),
                      ("Auth",        "PyJWT + passlib[bcrypt]", "JWT + хэширование"),
                      ("HTTP client", "httpx",                   "Async межсервисные вызовы"),
                      ("Config",      "pydantic-settings",       "12-factor env-конфиг"),
                      ("Logging",     "structlog",               "JSON-логи в stdout"),
                      ("Metrics",     "prometheus-client",       "Prometheus /metrics"),
                  ],
                  col_widths=[25 * mm, hw * 0.45, hw * 0.45])

    _simple_table(c, MARGIN + hw + 5 * mm, y,
                  ["Слой", "Технология", "Роль"],
                  [
                      ("Frontend",  "React 18 + Vite + TS",  "SPA"),
                      ("HTTP",      "axios",                  "API-клиент"),
                      ("Lint",      "ruff",                   "Linter + formatter"),
                      ("Tests",     "pytest",                 "Unit / integration"),
                      ("PDF",       "xhtml2pdf + ReportLab",  "PDF генерация"),
                      ("Templates", "Jinja2",                 "HTML шаблоны"),
                      ("Deps",      "uv",                     "Package manager"),
                      ("Build",     "Kaniko",                 "OCI-сборка без Docker"),
                      ("Registry",  "Harbor",                 "Container registry"),
                      ("IaC",       "Helm + ArgoCD",          "K8s charts + GitOps"),
                  ],
                  col_widths=[25 * mm, hw * 0.45, hw * 0.45])


def _sequence_diagram(c, x, y, w, participants, steps):
    """Draw a simple sequence diagram."""
    n = len(participants)
    col_w = w / n
    # Participant boxes
    ph = 9 * mm
    for i, p in enumerate(participants):
        px = x + i * col_w + col_w / 2 - 18 * mm
        _svg_box(c, px, y - ph, 36 * mm, ph, p)
        # Lifeline
        c.setStrokeColor(C_BORDER)
        c.setDash([2, 2])
        c.line(x + i * col_w + col_w / 2, y - ph, x + i * col_w + col_w / 2, y - ph - len(steps) * 9 * mm - 5 * mm)
        c.setDash([])

    # Steps
    for si, (from_i, to_i, label) in enumerate(steps):
        sy = y - ph - (si + 1) * 9 * mm
        fx = x + from_i * col_w + col_w / 2
        tx = x + to_i * col_w + col_w / 2
        _arrow(c, fx, sy, tx, sy)
        mx = (fx + tx) / 2
        c.setFont(FONT_REGULAR, 7)
        c.setFillColor(C_TEXT)
        c.drawCentredString(mx, sy + 2 * mm, label[:40])


def slide_07_auth_flow(c, n, total):
    _draw_slide_chrome(c, "Поток: Аутентификация и получение профиля", n, total)
    y = _start_content() - 3 * mm
    lw = CONTENT_W * 0.56

    _sequence_diagram(c, MARGIN, y, lw,
                      ["User", "Frontend", "Gateway", "auth-svc", "user-svc", "DB"],
                      [
                          (0, 1, "login form"),
                          (1, 2, "POST /auth/login"),
                          (2, 3, "/login"),
                          (3, 5, "check credentials"),
                          (5, 3, "user row"),
                          (3, 0, "access + refresh JWT"),
                          (1, 2, "GET /auth/me (Bearer)"),
                          (2, 3, "/me"),
                          (3, 4, "/internal/users/{id}"),
                          (4, 5, "read profile"),
                          (5, 0, "me DTO"),
                      ])

    rx = MARGIN + lw + 6 * mm
    rw = CONTENT_W - lw - 6 * mm
    _text(c, rx, PAGE_H - 34 * mm, "Детали реализации", font=FONT_BOLD, size=10)
    _box(c, rx, PAGE_H - 44 * mm - 20 * mm, rw, 20 * mm,
         title="Пользовательский JWT",
         lines=["access_token: HS256, TTL 15 мин",
                "refresh_token: TTL 7 дней (в БД)",
                "Payload: sub, role, iss, aud, exp"])
    _box(c, rx, PAGE_H - 44 * mm - 44 * mm, rw, 20 * mm,
         title="Internal JWT",
         lines=["Заголовок X-Internal-Token",
                "TTL 300 с, отдельный секрет",
                "Проверка iss / aud / exp"])
    _box(c, rx, PAGE_H - 44 * mm - 68 * mm, rw, 20 * mm,
         title="Хранение паролей",
         lines=["bcrypt через passlib",
                "Соль генерируется автоматически",
                "В БД хранится только хэш"])


def slide_08_test_flow(c, n, total):
    _draw_slide_chrome(c, "Поток: Прохождение теста и генерация отчёта", n, total)
    y = _start_content() - 3 * mm
    lw = CONTENT_W * 0.54

    _sequence_diagram(c, MARGIN, y, lw,
                      ["Employee", "Frontend", "Gateway", "test-svc", "llm-svc", "report-svc"],
                      [
                          (0, 1, "submit answers"),
                          (1, 2, "POST /attempts/{id}/submit"),
                          (2, 3, "forward"),
                          (3, 3, "save answers → DB"),
                          (3, 4, "POST /analyze (X-Internal)"),
                          (4, 3, "analysis result"),
                          (3, 5, "POST /reports (X-Internal)"),
                          (5, 5, "save report → DB"),
                          (5, 3, "report_id"),
                          (3, 3, "save score + report_id"),
                          (3, 0, "result + report link"),
                      ])

    rx = MARGIN + lw + 6 * mm
    rw = CONTENT_W - lw - 6 * mm
    _text(c, rx, PAGE_H - 34 * mm, "test-service — оркестратор", font=FONT_BOLD, size=10)
    _box(c, rx, PAGE_H - 42 * mm - 16 * mm, rw, 16 * mm,
         lines=["Единственный знает о полном бизнес-процессе.",
                "llm-service и report-service независимы",
                "и не знают друг о друге."], accent=True)
    _text(c, rx, PAGE_H - 42 * mm - 22 * mm, "Статусы назначения", font=FONT_BOLD, size=9)
    _simple_table(c, rx, PAGE_H - 42 * mm - 26 * mm,
                  ["Статус", "Описание"],
                  [("assigned",    "Тест назначен"),
                   ("in_progress", "Сотрудник начал"),
                   ("completed",   "Завершён, отчёт готов")],
                  col_widths=[rw * 0.4, rw * 0.6])
    _text(c, rx, PAGE_H - 42 * mm - 56 * mm, "LLM-провайдеры", font=FONT_BOLD, size=9)
    _simple_table(c, rx, PAGE_H - 42 * mm - 60 * mm,
                  ["ENV", "Поведение"],
                  [("mock",     "Детерминированный анализ (dev)"),
                   ("gigachat", "Реальный GigaChat API (OAuth2)")],
                  col_widths=[rw * 0.35, rw * 0.65])


def slide_09_data(c, n, total):
    _draw_slide_chrome(c, "Модель данных (PostgreSQL, schema-per-service)", n, total)
    y = _start_content() - 3 * mm
    lw = CONTENT_W * 0.52
    rw = CONTENT_W - lw - 6 * mm
    rx = MARGIN + lw + 6 * mm

    _text(c, MARGIN, y, "Ключевые сущности (схема tests)", font=FONT_BOLD, size=10)

    # ER diagram
    ew, eh = 36 * mm, 10 * mm
    ey = y - 8 * mm
    cx_mid = MARGIN + lw / 2
    # tests (center top)
    _svg_box(c, cx_mid - ew / 2, ey - eh, ew, eh, "tests", "id, title, created_by", accent=True)
    # questions (left)
    _svg_box(c, MARGIN + 2 * mm, ey - eh - 24 * mm, ew, eh, "questions", "id, test_id, type")
    # assignments (right)
    _svg_box(c, MARGIN + lw - ew - 2 * mm, ey - eh - 24 * mm, ew, eh, "assignments", "test_id, user_id, status")
    # attempts (center bottom)
    _svg_box(c, cx_mid - ew / 2, ey - eh - 48 * mm, ew, eh, "attempts", "assignment_id, score", accent=True)
    # answers (left bottom)
    _svg_box(c, MARGIN + 2 * mm, ey - eh - 48 * mm, ew, eh, "answers", "attempt_id, is_correct")
    # reports (right bottom)
    _svg_box(c, MARGIN + lw - ew - 2 * mm, ey - eh - 48 * mm, ew, eh, "reports", "attempt_id, summary")

    # Arrows
    _arrow(c, cx_mid - ew / 2, ey - eh - eh / 2, MARGIN + 2 * mm + ew / 2, ey - eh - 24 * mm + eh)
    _arrow(c, cx_mid + ew / 2, ey - eh - eh / 2, MARGIN + lw - 2 * mm - ew / 2, ey - eh - 24 * mm + eh)
    _arrow(c, MARGIN + lw - 2 * mm - ew / 2, ey - eh - 24 * mm, cx_mid + ew / 2, ey - eh - 48 * mm + eh)
    _arrow(c, cx_mid - ew / 2, ey - eh - 48 * mm + eh / 2, MARGIN + 2 * mm + ew, ey - eh - 48 * mm + eh / 2)
    _arrow(c, cx_mid + ew / 2, ey - eh - 48 * mm + eh / 2, MARGIN + lw - ew - 2 * mm, ey - eh - 48 * mm + eh / 2)

    # Right: schemas table
    _text(c, rx, y, "Все схемы PostgreSQL", font=FONT_BOLD, size=10)
    _simple_table(c, rx, y - 4 * mm,
                  ["Схема", "Сервис", "Ключевые таблицы"],
                  [
                      ("auth",    "auth-service",    "sessions"),
                      ("users",   "user-service",    "users, departments"),
                      ("tests",   "test-service",    "tests, questions, assignments, attempts, answers"),
                      ("llm",     "llm-service",     "analysis_results"),
                      ("reports", "report-service",  "reports"),
                  ],
                  col_widths=[rw * 0.2, rw * 0.28, rw * 0.52])

    _box(c, rx, PAGE_H - 42 * mm - 46 * mm, rw, 22 * mm,
         title="Решение: Enum в PostgreSQL",
         lines=["SQLAlchemy по умолчанию сохраняет NAME (FREE_TEXT),",
                "PostgreSQL ожидает VALUE (free_text).",
                "Исправлено: values_callable + validate_strings",
                "во всех Enum-колонках всех сервисов."],
         accent=True)


def slide_10_security(c, n, total):
    _draw_slide_chrome(c, "Безопасность", n, total)
    y = _start_content() - 3 * mm
    hw = (CONTENT_W - 5 * mm) / 2
    rx = MARGIN + hw + 5 * mm

    _text(c, MARGIN, y, "NetworkPolicy (default-deny)", font=FONT_BOLD, size=10)
    _simple_table(c, MARGIN, y - 4 * mm,
                  ["Политика", "Эффект"],
                  [
                      ("default-deny-all",        "Блокирует весь ingress/egress"),
                      ("allow-dns",               "UDP/TCP 53 → kube-system"),
                      ("allow-internal",          "Трафик внутри namespace app"),
                      ("allow-from-ingress",      "ingress-nginx → frontend + api-gw"),
                      ("allow-postgres-egress",   "app → database ns :5432"),
                      ("allow-llm-egress-external", "llm-service → Internet :443/:9443"),
                  ],
                  col_widths=[hw * 0.48, hw * 0.52])

    _box(c, MARGIN, y - 54 * mm - 15 * mm, hw, 15 * mm,
         title="Только llm-service может выходить в Интернет (GigaChat API)",
         lines=["Все остальные сервисы заблокированы от внешних соединений."],
         accent=True)

    _text(c, rx, y, "Container Security Context", font=FONT_BOLD, size=10)
    _simple_table(c, rx, y - 4 * mm,
                  ["Параметр", "Значение"],
                  [
                      ("runAsNonRoot",             "true"),
                      ("runAsUser / runAsGroup",   "10001 / 10001"),
                      ("readOnlyRootFilesystem",   "true"),
                      ("allowPrivilegeEscalation", "false"),
                      ("capabilities.drop",        "ALL"),
                      ("seccompProfile",           "RuntimeDefault"),
                  ],
                  col_widths=[hw * 0.55, hw * 0.45])

    _text(c, rx, y - 52 * mm, "Kubernetes Secrets", font=FONT_BOLD, size=9)
    _simple_table(c, rx, y - 56 * mm,
                  ["Secret", "Содержит"],
                  [
                      ("jwt-secret",          "Ключ пользовательского JWT"),
                      ("internal-jwt-secret", "Ключ service-to-service JWT"),
                      ("gigachat-creds",      "OAuth2 GigaChat"),
                      ("auth-db / users-db", "Per-service DB credentials"),
                  ],
                  col_widths=[hw * 0.45, hw * 0.55])


def slide_11_cicd(c, n, total):
    _draw_slide_chrome(c, "CI/CD пайплайн (Jenkins → Harbor → ArgoCD)", n, total)
    y = _start_content() - 3 * mm

    # Pipeline boxes
    stages = [
        ("git push", None),
        ("uv sync", None),
        ("ruff\npytest", None),
        ("Kaniko\nbuild", None),
        ("Harbor\nSHA+latest", None),
        ("Update\nHelm tags", None),
        ("ArgoCD\nsync", None),
        ("PreSync\nmigrate", None),
        ("Deploy\nrollout", None),
    ]
    ns = len(stages)
    sw = CONTENT_W / (ns + (ns - 1) * 0.2)
    gap = sw * 0.2
    sy = y - 2 * mm
    sh = 14 * mm
    for i, (lbl, _sub) in enumerate(stages):
        sx = MARGIN + i * (sw + gap)
        acc = (i == 0 or i == 6)
        _svg_box(c, sx, sy - sh, sw, sh, lbl.replace("\n", " "), accent=acc)
        if i < ns - 1:
            ax = sx + sw
            _arrow(c, ax, sy - sh / 2, ax + gap, sy - sh / 2)

    y -= sh + 6 * mm
    bw = (CONTENT_W - 6 * mm) / 3
    _box(c, MARGIN, y - 34 * mm, bw, 34 * mm,
         title="Kaniko (сборка)",
         lines=["Сборка OCI без Docker daemon",
                "Базовый образ education-python-base",
                "с cairo/pango для pycairo",
                "6 backend + 5 migrate + 1 frontend",
                "= 12 образов за один запуск",
                "Теги: git SHA + latest"])
    _box(c, MARGIN + bw + 3 * mm, y - 34 * mm, bw, 34 * mm,
         title="ArgoCD (деплой)",
         lines=["App-of-apps: root →",
                "  postgresql + education-platform",
                "sync-wave -20: PostgreSQL",
                "sync-wave -10: migrate Jobs (PreSync)",
                "sync-wave  0: Deployments",
                "selfHeal + prune: true"])
    _box(c, MARGIN + 2 * (bw + 3 * mm), y - 34 * mm, bw, 34 * mm,
         title="Оптимизации",
         lines=["Базовый Python-образ с системными",
                "пакетами (cairo, pango)",
                "Условная пересборка base по git diff",
                "Скип pipeline для deploy-only коммитов",
                "Таймауты на каждый build stage"])


def slide_12_k8s(c, n, total):
    _draw_slide_chrome(c, "Kubernetes деплой (Helm + ArgoCD)", n, total)
    y = _start_content() - 3 * mm
    hw = (CONTENT_W - 5 * mm) / 2
    rx = MARGIN + hw + 5 * mm

    _text(c, MARGIN, y, "Неймспейсы", font=FONT_BOLD, size=10)
    _simple_table(c, MARGIN, y - 4 * mm,
                  ["Namespace", "Содержит"],
                  [
                      ("app",          "6 backend сервисов + frontend"),
                      ("database",     "PostgreSQL StatefulSet"),
                      ("ingress-nginx", "Ingress controller"),
                      ("argocd",       "ArgoCD"),
                      ("jenkins",      "Jenkins"),
                      ("harbor",       "Container Registry"),
                      ("cert-manager", "TLS cert manager"),
                  ],
                  col_widths=[hw * 0.38, hw * 0.62])

    _text(c, MARGIN, y - 62 * mm, "Ingress (TLS)", font=FONT_BOLD, size=9)
    _simple_table(c, MARGIN, y - 66 * mm,
                  ["Host", "Service"],
                  [("app.mokryakov.local", "frontend :8080"),
                   ("api.mokryakov.local", "api-gateway :8080")],
                  col_widths=[hw * 0.55, hw * 0.45])

    _text(c, rx, y, "Каждый Deployment", font=FONT_BOLD, size=10)
    _box(c, rx, y - 4 * mm - 40 * mm, hw, 40 * mm,
         lines=["requests: CPU 50m / RAM 96Mi",
                "limits:   CPU 500m / RAM 512Mi",
                "livenessProbe:  GET /healthz",
                "readinessProbe: GET /readyz",
                "securityContext: non-root, readOnly FS",
                "capabilities.drop: ALL",
                "ServiceAccount: education-platform",
                "imagePullSecrets: harbor-pull-secret"])

    _text(c, rx, y - 50 * mm, "ArgoCD sync-waves", font=FONT_BOLD, size=9)
    _simple_table(c, rx, y - 54 * mm,
                  ["Wave", "Ресурс"],
                  [("-20", "PostgreSQL (отдельный Helm release)"),
                   ("-10", "Migrate Jobs (PreSync hook)"),
                   ("0",   "Deployments + Services + Ingress")],
                  col_widths=[hw * 0.15, hw * 0.85])


def slide_13_problems(c, n, total):
    _draw_slide_chrome(c, "Ключевые инженерные решения", n, total)
    y = _start_content() - 3 * mm
    bw = (CONTENT_W - 5 * mm) / 2
    bh = (y - 14 * mm - 10 * mm) / 2

    cards = [
        ("Enum mismatch в PostgreSQL",
         ["Симптом: InvalidTextRepresentationError: FREE_TEXT",
          "SQLAlchemy пишет NAME, PostgreSQL ожидает VALUE.",
          "Решение: values_callable=_enum_values +",
          "validate_strings=True во всех Enum-колонках."]),
        ("MissingGreenlet (async lazy load)",
         ["Симптом: greenlet_spawn has not been called",
          "len(t.questions) вне async-сессии → lazy load.",
          "Решение: заменён на scalar_subquery() —",
          "count считается в основном SQL-запросе."]),
        ("Кириллица в PDF отчётах",
         ["Симптом: все русские буквы → nnnn...",
          "xhtml2pdf не применял CSS @font-face.",
          "Решение: явная регистрация DejaVuSans:",
          "pdfmetrics.registerFont(TTFont(...)) перед pisa."]),
        ("pycairo в Kaniko (apt системные пакеты)",
         ["Симптом: pkg-config for cairo not found",
          "pycairo требует cairo/pango при сборке.",
          "Решение: базовый образ education-python-base",
          "с предустановленными системными пакетами."]),
    ]
    for i, (title, lines) in enumerate(cards):
        col = i % 2
        row = i // 2
        bx = MARGIN + col * (bw + 5 * mm)
        by = y - row * (bh + 4 * mm) - bh
        _box(c, bx, by, bw, bh, title=title, lines=lines, accent=(i % 2 == 0))
        _pill(c, bx + bw - 24 * mm, by + bh - 2 * mm,
              ["SQLAlchemy", "SQLAlchemy", "PDF/ReportLab", "Kaniko/Docker"][i],
              tone=["danger", "danger", "warn", "warn"][i])


def slide_14_frontend(c, n, total):
    _draw_slide_chrome(c, "Frontend (React 18 + Vite + TypeScript)", n, total)
    y = _start_content() - 3 * mm
    hw = (CONTENT_W - 5 * mm) / 2
    rx = MARGIN + hw + 5 * mm

    _text(c, MARGIN, y, "Страницы по ролям (RBAC)", font=FONT_BOLD, size=10)
    _simple_table(c, MARGIN, y - 4 * mm,
                  ["Роль", "Страницы"],
                  [
                      ("employee", "Список назначений, прохождение теста, результаты, профиль"),
                      ("manager",  "Создание/редакт. тестов, назначение, просмотр попыток/отчётов"),
                      ("admin",    "Управление пользователями + все страницы manager"),
                  ],
                  col_widths=[hw * 0.22, hw * 0.78])

    _text(c, MARGIN, y - 36 * mm, "Архитектурные решения", font=FONT_BOLD, size=9)
    _box(c, MARGIN, y - 42 * mm - 28 * mm, hw, 28 * mm,
         lines=["• Guard HOC — защита роутов по роли из JWT",
                "• axios instance с Bearer token из localStorage",
                "• Централизованный API-слой (api.ts)",
                "• Reset setError(null) + setData(null) в useEffect",
                "  при смене route (fix: страницы без refresh)",
                "• Поиск по тестам для manager/admin"])

    _text(c, rx, y, "Сборка и деплой", font=FONT_BOLD, size=10)
    _box(c, rx, y - 4 * mm - 20 * mm, hw, 20 * mm,
         lines=["npm run build → статика в nginx-unprivileged",
                "API URL через VITE_API_URL (build arg)",
                "Ingress: app.mokryakov.local → frontend pod",
                "TLS: cert-manager + mokryakov-ca"])

    _text(c, rx, y - 28 * mm, "Исправленная проблема", font=FONT_BOLD, size=9)
    _box(c, rx, y - 34 * mm - 26 * mm, hw, 26 * mm,
         title="Страницы не загружались без refresh",
         lines=["При SPA-навигации старые error-состояния",
                "блокировали новые fetch-запросы.",
                "Решение: явный сброс setError(null) +",
                "setData(null) в начале каждого useEffect",
                "перед запросом к API."],
         accent=True)


def slide_15_conclusion(c, n, total):
    _draw_slide_chrome(c, "Результаты и выводы", n, total)
    y = _start_content() - 3 * mm

    _stat_strip(c, MARGIN, y, [
        ("6",      "Backend микросервисов"),
        ("12",     "Docker образов в Harbor"),
        ("5",      "Независимых схем БД"),
        ("100%",   "Критериев готовности"),
        ("GitOps", "Стратегия деплоя"),
        ("0",      "Секретов в коде"),
    ])
    y -= 22 * mm

    hw = (CONTENT_W - 5 * mm) / 2
    rx = MARGIN + hw + 5 * mm

    _text(c, MARGIN, y, "Что реализовано", font=FONT_BOLD, size=10)
    for line in [
        "• Production-ready микросервисная архитектура на Python/FastAPI",
        "• Полный CI/CD: Jenkins + Kaniko + Harbor + ArgoCD",
        "• Self-hosted Kubernetes с GitOps (ArgoCD app-of-apps)",
        "• Security-by-default: NetworkPolicy, non-root, drop ALL caps",
        "• LLM-интеграция с подменяемым провайдером (mock / GigaChat)",
        "• Prometheus-метрики, JSON-логи, healthcheck на каждом сервисе",
    ]:
        y -= 6 * mm
        c.setFont(FONT_REGULAR, 9)
        c.setFillColor(C_TEXT)
        c.drawString(MARGIN, y, line)

    y_r = _start_content() - 25 * mm
    _text(c, rx, y_r, "Потенциал развития", font=FONT_BOLD, size=10)
    for line in [
        "• Асинхронная очередь (NATS/Kafka) вместо синхронного HTTP",
        "• Мониторинг: Prometheus + Grafana + Loki + Alertmanager",
        "• Horizontal Pod Autoscaler по RPS",
        "• Разделение PostgreSQL по физическим инстансам",
        "• Rate limiting и circuit breaker на API Gateway",
        "• RBAC на уровне Kubernetes",
    ]:
        y_r -= 6 * mm
        c.setFont(FONT_REGULAR, 9)
        c.setFillColor(C_TEXT)
        c.drawString(rx, y_r, line)

    # Final callout
    cy = min(y, y_r) - 10 * mm
    _box(c, MARGIN, cy - 18 * mm, CONTENT_W, 18 * mm,
         title="Вывод",
         lines=["Разработана и задеплоена полноценная производственная платформа с микросервисной архитектурой,",
                "автоматическим CI/CD и декларативным управлением инфраструктурой через GitOps.",
                "Все 14 критериев готовности, заявленных в техническом задании, выполнены."],
         accent=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

SLIDES = [
    slide_01_title,
    slide_02_goals,
    slide_03_infra,
    slide_04_arch,
    slide_05_services,
    slide_06_stack,
    slide_07_auth_flow,
    slide_08_test_flow,
    slide_09_data,
    slide_10_security,
    slide_11_cicd,
    slide_12_k8s,
    slide_13_problems,
    slide_14_frontend,
    slide_15_conclusion,
]


def main():
    _register_fonts()

    out_path = Path(__file__).parent.parent / "docs" / "diploma-presentation.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = pdf_canvas.Canvas(str(out_path), pagesize=landscape(A4))
    c.setTitle("Микросервисная платформа обучения и тестирования сотрудников")
    c.setAuthor("Дипломная работа")

    total = len(SLIDES)
    for i, slide_fn in enumerate(SLIDES, start=1):
        print(f"  Рендеринг слайда {i}/{total}: {slide_fn.__name__}")
        slide_fn(c, i, total)
        c.showPage()

    c.save()
    print(f"\nГотово! PDF сохранён: {out_path.resolve()}")


if __name__ == "__main__":
    main()
