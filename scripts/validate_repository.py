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
    "docs/assessment-system.md",
    "docs/quality-checklist.md",
    "docs/review-guide.md",
    "Project/README.md",
    "Exam/README.md",
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
