#!/usr/bin/env python3
"""Generate the vector architecture diagram used as Figure 1."""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas


PAGE_WIDTH = 514.8
PAGE_HEIGHT = 396.0

INK = HexColor("#24364b")
MUTED = HexColor("#667487")
BLUE = HexColor("#0077b6")
BLUE_FILL = HexColor("#f1f7fb")
GREEN = HexColor("#008c73")
GREEN_FILL = HexColor("#f1f8f5")
ORANGE = HexColor("#c66a00")
ORANGE_FILL = HexColor("#fff8ef")
SLATE = HexColor("#64748b")
GRAY_FILL = HexColor("#f7f7f8")
SEPARATOR = HexColor("#9aa5b1")


def centered(
    page: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    size: float,
    *,
    bold: bool = False,
    italic: bool = False,
    color=INK,
) -> None:
    if bold and italic:
        font = "Helvetica-BoldOblique"
    elif bold:
        font = "Helvetica-Bold"
    elif italic:
        font = "Helvetica-Oblique"
    else:
        font = "Helvetica"
    page.setFont(font, size)
    page.setFillColor(color)
    page.drawCentredString(x, y, text)


def box(
    page: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    stroke=BLUE,
    fill=BLUE_FILL,
    dashed: bool = False,
    radius: float = 3.5,
) -> None:
    page.setFillColor(fill)
    page.setStrokeColor(stroke)
    page.setLineWidth(0.9)
    if dashed:
        page.setDash(3, 2)
    page.roundRect(x, y, width, height, radius, fill=1, stroke=1)
    page.setDash()


def arrow(
    page: canvas.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    dashed: bool = False,
    color=SLATE,
    width: float = 0.8,
) -> None:
    page.setStrokeColor(color)
    page.setFillColor(color)
    page.setLineWidth(width)
    if dashed:
        page.setDash(3, 2)
    page.line(x1, y1, x2, y2)
    page.setDash()

    head = 3.5
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 >= x1 else -1
        points = [(x2, y2), (x2 - sign * head, y2 + 2.0), (x2 - sign * head, y2 - 2.0)]
    else:
        sign = 1 if y2 >= y1 else -1
        points = [(x2, y2), (x2 + 2.0, y2 - sign * head), (x2 - 2.0, y2 - sign * head)]
    path = page.beginPath()
    path.moveTo(*points[0])
    path.lineTo(*points[1])
    path.lineTo(*points[2])
    path.close()
    page.drawPath(path, fill=1, stroke=0)


def polyline_arrow(page: canvas.Canvas, points: list[tuple[float, float]], *, color=SLATE) -> None:
    page.setStrokeColor(color)
    page.setLineWidth(0.8)
    path = page.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    page.drawPath(path, fill=0, stroke=1)
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    page.setFillColor(color)
    head = 3.5
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 >= x1 else -1
        triangle = [(x2, y2), (x2 - sign * head, y2 + 2.0), (x2 - sign * head, y2 - 2.0)]
    else:
        sign = 1 if y2 >= y1 else -1
        triangle = [(x2, y2), (x2 + 2.0, y2 - sign * head), (x2 - 2.0, y2 - sign * head)]
    head_path = page.beginPath()
    head_path.moveTo(*triangle[0])
    head_path.lineTo(*triangle[1])
    head_path.lineTo(*triangle[2])
    head_path.close()
    page.drawPath(head_path, fill=1, stroke=0)


def generate(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".pdf",
        prefix="figure1-",
        dir=output_path.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)

    page = canvas.Canvas(
        str(temporary_path), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1
    )
    page.setTitle("Evidence-Bounded Cross-Modal Relation Ledger workflow")
    page.setAuthor("ICIT2027 authors")

    centered(page, "Model-visible method path", 205, 380, 11.0, bold=True)
    centered(page, "Evaluator-only path", 454, 380, 9.2, bold=True)

    page.setStrokeColor(SEPARATOR)
    page.setLineWidth(0.9)
    page.setDash(3, 2)
    page.line(397, 18, 397, 368)
    page.setDash()

    box(page, 15, 321, 112, 48, stroke=SLATE, fill=white, dashed=True)
    centered(page, "Upstream alert source", 71, 356, 6.8, bold=True)
    centered(page, "PASAD | Invariants | Seq2Seq", 71, 345, 4.7)
    centered(page, "SIMPLE | GeCo | analyst", 71, 335.5, 4.9)
    centered(page, "outside evaluation", 71, 325, 5.1, italic=True, color=MUTED)

    box(page, 143, 331, 108, 38)
    centered(page, "Supplied event scope", 197, 355, 7.0, bold=True)
    centered(page, "window W_e + anchor t_0", 197, 342, 6.0)

    box(page, 267, 331, 116, 38)
    centered(page, "Visible evidence B_e", 325, 355, 7.0, bold=True)
    centered(page, "network | telemetry | maps", 325, 342, 5.9)
    arrow(page, 127, 350, 143, 350, dashed=True)

    box(page, 88, 276, 212, 39)
    centered(page, "1  Deterministic episode normalization", 194, 301, 7.6, bold=True)
    centered(page, "command transactions Q_e | telemetry changes P'_e | stable IDs", 194, 287, 5.8)
    polyline_arrow(page, [(197, 331), (197, 315)])
    polyline_arrow(page, [(325, 331), (325, 322), (270, 322), (270, 315)])

    box(page, 88, 222, 212, 39)
    centered(page, "2  Frozen candidate pairs C_e", 194, 247, 7.6, bold=True)
    centered(page, "permissive time/asset strata | identical denominator", 194, 233, 5.9)
    arrow(page, 194, 276, 194, 261)

    box(page, 88, 168, 212, 39)
    centered(page, "3  EBRL relation proposer", 194, 193, 7.6, bold=True)
    centered(page, "link | supported non-link | insufficient evidence", 194, 179, 5.9)
    arrow(page, 194, 222, 194, 207)

    box(page, 88, 112, 212, 41, stroke=GREEN, fill=GREEN_FILL)
    centered(page, "4  Structured relation ledger", 194, 138, 7.6, bold=True)
    centered(page, "level R0-R4 | typed evidence path | flags | reason", 194, 124, 5.8)
    arrow(page, 194, 168, 194, 153)

    box(page, 88, 58, 212, 39, stroke=GREEN, fill=GREEN_FILL)
    centered(page, "5  Visible-only publication verifier", 194, 83, 7.4, bold=True)
    centered(page, "retain | downgrade | suppress; no evaluator labels", 194, 69, 5.8)
    arrow(page, 194, 112, 194, 97)

    box(page, 88, 13, 212, 29, stroke=GREEN, fill=GREEN_FILL)
    centered(page, "Bounded report rendered from admitted rows", 194, 24, 6.8, bold=True)
    arrow(page, 194, 58, 194, 42)

    box(page, 311, 218, 72, 47, stroke=ORANGE, fill=ORANGE_FILL)
    centered(page, "B0-B6 baselines", 347, 249, 6.4, bold=True)
    centered(page, "same candidates", 347, 237, 5.6)
    centered(page, "same ledger schema", 347, 227, 5.4)
    arrow(page, 300, 241.5, 311, 241.5)

    box(page, 408, 326, 93, 44, stroke=SLATE, fill=GRAY_FILL)
    centered(page, "Hidden provenance", 454.5, 354, 6.7, bold=True)
    centered(page, "action/state trace", 454.5, 342, 5.8)
    centered(page, "scenario log", 454.5, 332, 5.8)

    box(page, 408, 258, 93, 50, stroke=SLATE, fill=GRAY_FILL)
    centered(page, "Reference builder", 454.5, 291, 6.7, bold=True)
    centered(page, "operational status", 454.5, 280, 5.6)
    centered(page, "visible ceiling", 454.5, 270, 5.6)
    centered(page, "+ provenance", 454.5, 261, 5.5)
    arrow(page, 454.5, 326, 454.5, 308)

    box(page, 408, 204, 93, 37, stroke=SLATE, fill=GRAY_FILL)
    centered(page, "Frozen references", 454.5, 227, 6.6, bold=True)
    centered(page, "scoring only", 454.5, 214, 5.7, italic=True, color=MUTED)
    arrow(page, 454.5, 258, 454.5, 241)

    box(page, 408, 111, 93, 72, stroke=SLATE, fill=GRAY_FILL)
    centered(page, "Independent scorer", 454.5, 167, 6.7, bold=True)
    centered(page, "raw + published", 454.5, 153, 5.7)
    centered(page, "ledgers vs refs.", 454.5, 142, 5.7)
    centered(page, "event-level metrics", 454.5, 126, 5.6)
    arrow(page, 454.5, 204, 454.5, 183)

    box(page, 408, 42, 93, 50, stroke=GREEN, fill=GREEN_FILL)
    centered(page, "Evaluation", 454.5, 77, 6.8, bold=True)
    centered(page, "recovery | false links", 454.5, 64, 5.5)
    centered(page, "overpromotion | abstain", 454.5, 53, 5.3)
    arrow(page, 454.5, 111, 454.5, 92)

    polyline_arrow(page, [(300, 132.5), (389, 132.5), (389, 158), (408, 158)])
    polyline_arrow(page, [(300, 77.5), (380, 77.5), (380, 126), (408, 126)])
    polyline_arrow(page, [(383, 241.5), (392, 241.5), (392, 174), (408, 174)])
    centered(page, "never enters method", 454.5, 194, 5.5, italic=True, color=MUTED)

    page.showPage()
    page.save()
    temporary_path.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("figures/figure1_system_architecture.pdf"),
    )
    args = parser.parse_args()
    generate(args.output)


if __name__ == "__main__":
    main()
