#!/usr/bin/env python3
"""Validate structure, local links, KIM completeness, markers, and point totals."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSE-CODE.md",
    "docs/rpd.md",
    "docs/competency-model.md",
    "docs/fos.md",
    "docs/semester-guide.md",
    "docs/assessment-system.md",
    "docs/quality-checklist.md",
    "docs/review-guide.md",
    "Project/README.md",
    "Exam/README.md",
    "Exam/presentation-guide.md",
    "Exam/speech-outline.md",
    "Exam/defense-protocol.md",
    "Entry/README.md",
    "Entry/kim-00-diagnostic.md",
    "Entry/remediation-map.md",
    "team/README.md",
    "data/krm-v3.0.xlsx",
    "requirements.txt",
]

MODULES = [
    ("M1-task-formulation", "kim-01-project-brief.md", "rubric-01.md"),
    ("M2-data-understanding", "kim-02-eda.md", "rubric-02.md"),
    ("M3-data-preparation", "kim-03-data-preparation.md", "rubric-03.md"),
    ("M4-modeling", "kim-04-modeling.md", "rubric-04.md"),
    ("M5-evaluation", "kim-05-validation.md", "rubric-05.md"),
    ("M6-analytical-product", "kim-06-analytical-report.md", "rubric-06.md"),
]

FORBIDDEN_MARKERS = [
    "[ЗАПОЛНИТЬ]",
    "[НАЗВАНИЕ ДИСЦИПЛИНЫ]",
    "[НАЗВАНИЕ МОДУЛЯ]",
    "M1-module-name",
    "M2-module-name",
    "kim-01-template",
]

KIM_REQUIRED_HEADINGS = [
    "## Назначение",
    "## Проверяем",
    "## Задание",
    "## Оценивание",
    "## Внешние ресурсы и генеративный ИИ",
]

LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
POINT_PATTERN = re.compile(r"^\| (?:Модуль [1-6]|Зачёт) \|.*\| (\d+) \|$", re.MULTILINE)

TARGET_COVERAGE = {
    "LC-1.1": [
        "M1-task-formulation/kim-01-project-brief.md",
        "M6-analytical-product/kim-06-analytical-report.md",
        "Exam/README.md",
    ],
    "BD-1.2": [
        "M2-data-understanding/kim-02-eda.md",
        "M6-analytical-product/kim-06-analytical-report.md",
        "Exam/README.md",
    ],
    "BD-1.3": [
        "M3-data-preparation/kim-03-data-preparation.md",
        "M6-analytical-product/kim-06-analytical-report.md",
        "Exam/README.md",
    ],
    "BD-1.5": [
        "M3-data-preparation/kim-03-data-preparation.md",
        "M6-analytical-product/kim-06-analytical-report.md",
        "Exam/README.md",
    ],
    "ML-2.1": [
        "M4-modeling/kim-04-modeling.md",
        "M6-analytical-product/kim-06-analytical-report.md",
        "Exam/README.md",
    ],
    "ML-2.2": [
        "M3-data-preparation/kim-03-data-preparation.md",
        "M4-modeling/kim-04-modeling.md",
        "M6-analytical-product/kim-06-analytical-report.md",
        "Exam/README.md",
    ],
    "ML-2.3": [
        "M5-evaluation/kim-05-validation.md",
        "M6-analytical-product/kim-06-analytical-report.md",
        "Exam/README.md",
    ],
}

ENTRY_INDICATORS = [
    "ВК-1.1",
    "ВК-1.2",
    "ВК-2.1",
    "ВК-2.2",
    "ВК-3.1",
    "ВК-3.2",
    "ВК-4.1",
    "ВК-4.2",
]

FOS_MATRIX = {
    "КИМ-1": [10, 0, 0, 0, 0, 0, 0, 10],
    "КИМ-2": [0, 15, 0, 0, 0, 0, 0, 15],
    "КИМ-3": [0, 0, 6, 5, 0, 4, 0, 15],
    "КИМ-4": [0, 0, 0, 0, 12, 8, 0, 20],
    "КИМ-5": [0, 0, 0, 0, 0, 0, 15, 15],
    "КИМ-6": [2, 2, 2, 2, 2, 2, 3, 15],
    "Защита": [2, 1, 1, 1, 1, 1, 3, 10],
}


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)


def check_required(errors: list[str]) -> None:
    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).exists():
            errors.append(f"missing required path: {relative}")
    for module, kim, rubric in MODULES:
        for relative in (f"{module}/README.md", f"{module}/{kim}", f"{module}/{rubric}"):
            if not (ROOT / relative).is_file():
                errors.append(f"missing module file: {relative}")


def check_markers(errors: list[str]) -> None:
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                errors.append(f"unresolved marker {marker!r}: {path.relative_to(ROOT)}")


def check_links(errors: list[str]) -> None:
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            file_part = unquote(target.split("#", 1)[0])
            if not file_part:
                continue
            resolved = (path.parent / file_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"link escapes repository: {path.relative_to(ROOT)} -> {target}")
                continue
            if not resolved.exists():
                errors.append(f"broken local link: {path.relative_to(ROOT)} -> {target}")


def check_kim_sections(errors: list[str]) -> None:
    for module, kim, _ in MODULES:
        path = ROOT / module / kim
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for heading in KIM_REQUIRED_HEADINGS:
            if heading not in text:
                errors.append(f"missing KIM section {heading!r}: {path.relative_to(ROOT)}")


def check_points(errors: list[str]) -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    points = [int(value) for value in POINT_PATTERN.findall(text)]
    if points != [10, 15, 15, 20, 15, 15, 10]:
        errors.append(f"unexpected assessment point sequence: {points}")
    if sum(points) != 100:
        errors.append(f"assessment points sum to {sum(points)}, expected 100")


def check_indicator_coverage(errors: list[str]) -> None:
    for indicator, relative_paths in TARGET_COVERAGE.items():
        for relative in relative_paths:
            path = ROOT / relative
            if path.exists() and indicator not in path.read_text(encoding="utf-8"):
                errors.append(f"indicator {indicator} missing from {relative}")

    entry_text = (ROOT / "Entry/kim-00-diagnostic.md").read_text(encoding="utf-8")
    for indicator in ENTRY_INDICATORS:
        if indicator not in entry_text:
            errors.append(f"entry indicator missing from diagnostic: {indicator}")


def check_fos_matrix(errors: list[str]) -> None:
    text = (ROOT / "docs/fos.md").read_text(encoding="utf-8")
    found: dict[str, list[int]] = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 9 or cells[0] not in FOS_MATRIX:
            continue
        try:
            found[cells[0]] = [int(value) for value in cells[1:]]
        except ValueError:
            errors.append(f"non-numeric FOS matrix row: {cells[0]}")

    if found != FOS_MATRIX:
        errors.append(f"unexpected FOS matrix: {found}")

    if found:
        column_totals = [sum(row[index] for row in found.values()) for index in range(8)]
        if column_totals != [14, 18, 9, 8, 15, 15, 21, 100]:
            errors.append(f"unexpected FOS column totals: {column_totals}")


def check_files(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name.startswith("~$") or path.suffix.lower() == ".tmp":
            errors.append(f"temporary file tracked: {path.relative_to(ROOT)}")
        if path.stat().st_size >= 95 * 1024 * 1024:
            errors.append(f"file is too large for regular GitHub storage: {path.relative_to(ROOT)}")


def main() -> int:
    errors: list[str] = []
    check_required(errors)
    check_markers(errors)
    check_links(errors)
    check_kim_sections(errors)
    check_points(errors)
    check_indicator_coverage(errors)
    check_fos_matrix(errors)
    check_files(errors)

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Repository validation passed: {len(markdown_files())} Markdown files checked.")
    print("Manual publication checks remain: team identities, OPOP metadata, and license approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
