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
    page.setTitle("Evidence-bounded OT investigation with versioned skill contracts")
    page.setAuthor("ICIT2027 authors")

    centered(page, "Evidence-bounded post-alert OT investigation", 176, 379, 11.5, bold=True)
    centered(page, "Evaluation only", 454, 379, 9.2, bold=True)

    source_y, source_h = 327, 39
    source_w = 111
    for x, title, subtitle in (
        (18, "Electrical/process (E)", "Reported observations"),
        (139, "Network (N)", "Messages and timing"),
        (260, "Static metadata (M)", "Approved mappings"),
    ):
        box(page, x, source_y, source_w, source_h)
        centered(page, title, x + source_w / 2, source_y + 24, 7.3, bold=True)
        centered(page, subtitle, x + source_w / 2, source_y + 11.5, 6.7)

    box(page, 18, 276, 353, 37)
    centered(page, "Evidence construction + case trace", 194.5, 298, 8.2, bold=True)
    centered(
        page,
        "stable IDs | source/time | units/assets | parent lineage | policy/review state",
        194.5,
        284.5,
        5.9,
    )
    for x in (73.5, 194.5, 315.5):
        arrow(page, x, source_y, x, 313)

    page.setStrokeColor(SEPARATOR)
    page.setLineWidth(0.8)
    page.setDash(3, 2)
    page.line(394, 44, 394, 369)
    page.setDash()

    box(page, 18, 214, 119, 49, stroke=SLATE, fill=white, dashed=True)
    centered(page, "External alert sources", 77.5, 248, 6.7, bold=True)
    centered(page, "PASAD / Invariants / Seq2SeqNN", 77.5, 237, 5.2)
    centered(page, "SIMPLE / GeCo / operator alert", 77.5, 227, 5.2)
    centered(page, "handoff: scope + t0", 77.5, 217.5, 5.3, italic=True, color=MUTED)

    box(page, 151, 207, 220, 56)
    centered(page, "Boundary gate + scoped retrieval skill", 261, 248, 7.8, bold=True)
    centered(page, "case_id | scope/t0 | approved view | read-only", 261, 235.5, 6.2)
    centered(page, "E: <=64 | N: <=64 | EN: <=32 E + <=32 N", 261, 224.2, 6.3)
    centered(page, "fixed record/field and serialized-input limits", 261, 213.5, 5.8, color=MUTED)
    arrow(page, 194.5, 276, 194.5, 263)
    arrow(page, 137, 238.5, 151, 238.5, dashed=True)

    centered(page, "Prompt/skill does not", 77.5, 197, 6.0, color=MUTED)
    centered(page, "grant data access", 77.5, 187, 6.0, color=MUTED)
    centered(page, "enforcement is external", 77.5, 177, 5.6, italic=True, color=MUTED)

    box(page, 132, 148, 239, 45)
    centered(page, "Versioned investigation skills (combined here)", 251.5, 178.5, 7.6, bold=True)
    centered(page, "triage | timeline | competing hypotheses", 251.5, 166.3, 6.4)
    centered(page, "typed claims | explicit unknowns | visible evidence IDs", 251.5, 155.3, 6.0)
    arrow(page, 261, 207, 261, 193)

    box(page, 132, 92, 239, 43, stroke=GREEN, fill=GREEN_FILL)
    centered(page, "Report-review skill + deterministic publication gate", 251.5, 119.5, 7.4, bold=True)
    centered(page, "visible refs | values/units | assets/time | lineage", 251.5, 107.5, 6.0)
    centered(page, "frozen finite claim-support policy", 251.5, 97.5, 5.9)
    arrow(page, 251.5, 148, 251.5, 135)
    centered(page, "Exact G1-EN replay", 308, 140.5, 5.8, color=INK)

    polyline_arrow(page, [(77.5, 174), (77.5, 113.5), (132, 113.5)])
    centered(page, "same bounded", 77.5, 151, 5.9, color=MUTED)
    centered(page, "evidence bundle", 77.5, 141.5, 5.9, color=MUTED)

    outcome_y, outcome_h, outcome_w = 51, 29, 92
    for x, title, stroke, fill in (
        (18, "SUPPORTED", GREEN, GREEN_FILL),
        (123, "QUALIFIED", GREEN, GREEN_FILL),
        (228, "INSUFFICIENT", ORANGE, ORANGE_FILL),
    ):
        box(page, x, outcome_y, outcome_w, outcome_h, stroke=stroke, fill=fill)
        centered(page, title, x + outcome_w / 2, outcome_y + 11, 6.8, bold=True)
    page.setStrokeColor(SLATE)
    page.setLineWidth(0.8)
    page.line(251.5, 92, 251.5, 85)
    page.line(64, 85, 274, 85)
    for x in (64, 169, 274):
        arrow(page, x, 85, x, 80)

    box(page, 18, 12, 197, 27, stroke=GREEN, fill=GREEN_FILL)
    centered(page, "V1-EN: publish findings + explicit limitations", 116.5, 22.5, 6.3, bold=True)
    arrow(page, 64, 51, 64, 39)
    arrow(page, 169, 51, 169, 39)
    centered(page, "claim withheld; limitation only if explicit", 274, 30.5, 5.5, color=ORANGE)

    box(page, 407, 325, 94, 41, stroke=SLATE, fill=GRAY_FILL)
    centered(page, "Evaluator refs. (G)", 454, 349, 7.2, bold=True)
    centered(page, "facts + review rules", 454, 337, 6.2)
    centered(page, "evaluator only", 454, 327.5, 5.9, color=MUTED)

    box(page, 407, 158, 94, 142, stroke=SLATE, fill=GRAY_FILL)
    centered(page, "Frozen scoring", 454, 283, 7.5, bold=True)
    centered(page, "single R1 reviewer", 454, 236, 6.3)
    centered(page, "32 final events", 454, 225, 6.3)
    centered(page, "event-level metrics", 454, 214, 6.3)
    centered(page, "paired contrasts", 454, 203, 6.3)
    arrow(page, 454, 325, 454, 300)

    polyline_arrow(page, [(371, 170.5), (400, 170.5), (400, 229), (407, 229)])
    polyline_arrow(page, [(215, 25.5), (387, 25.5), (387, 177), (407, 177)])
    centered(page, "No evaluator refs. to", 454, 95, 6.0, color=MUTED)
    centered(page, "retrieval, skills,", 454, 84, 6.0, color=MUTED)
    centered(page, "or verification", 454, 73, 6.0, color=MUTED)

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
