#!/usr/bin/env python3
"""Validate structure, local links, KIM completeness, markers, and point totals."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ipynb_checkpoints",
}

REQUIRED_PATHS = [
    "README.md",
    ".gitattributes",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSE-CODE.md",
    "docs/rpd.md",
    "docs/competency-model.md",
    "docs/role-trajectory.md",
    "docs/measurement-model.md",
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
    "requirements-lock.txt",
    "scripts/smoke_test.py",
]

MODULES = [
    ("M1-task-formulation", "kim-01-project-brief.md", "rubric-01.md"),
    ("M2-data-understanding", "kim-02-eda.md", "rubric-02.md"),
    ("M3-data-preparation", "kim-03-data-preparation.md", "rubric-03.md"),
    ("M4-modeling", "kim-04-modeling.md", "rubric-04.md"),
    ("M5-evaluation", "kim-05-validation.md", "rubric-05.md"),
    ("M6-analytical-product", "kim-06-analytical-report.md", "rubric-06.md"),
]

SYNTHETIC_CASE_PATHS = [
    "examples/synthetic-case/README.md",
    "examples/synthetic-case/LICENSE-DATA.md",
    "examples/synthetic-case/requirements.txt",
    "examples/synthetic-case/generate_data.py",
    "examples/synthetic-case/generate_variants.py",
    "examples/synthetic-case/data/subscriber_retention.csv",
    "examples/synthetic-case/data/generation-manifest.json",
    "examples/synthetic-case/data/schema.json",
    "examples/synthetic-case/src/__init__.py",
    "examples/synthetic-case/src/data_preparation.py",
    "examples/synthetic-case/student/starter.ipynb",
    "examples/synthetic-case/teacher/baseline.py",
    "examples/synthetic-case/teacher/expected_metric_ranges.json",
    "examples/synthetic-case/teacher/reference-output/baseline-metrics.json",
    "examples/synthetic-case/teacher/reference-output/experiment-log.csv",
    "examples/synthetic-case/tests/test_case.py",
]

FORBIDDEN_MARKERS = [
    "[ЗАПОЛНИТЬ]",
    "[НАЗВАНИЕ ДИСЦИПЛИНЫ]",
    "[НАЗВАНИЕ МОДУЛЯ]",
    "M1-module-name",
    "M2-module-name",
    "kim-01-template",
]

FORBIDDEN_MARKER_PATTERNS = [
    re.compile(
        r"\[(?:ЗАПОЛНИТЬ|ФИО|ОПОП|ДАТА|СЕМЕСТР|ОРГАНИЗАЦИЯ|"
        r"НАЗВАНИЕ(?:\s+[^\]]+)?)\]",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:TODO|TBD|PLACEHOLDER|FIXME|XXX)\b", re.IGNORECASE),
    re.compile(r"\{\{[^{}\r\n]+\}\}"),
    re.compile(r"<<[^<>\r\n]+>>"),
]

KIM_REQUIRED_HEADINGS = [
    "## Назначение",
    "## Проверяем",
    "## Задание",
    "## Оценивание",
    "## Внешние ресурсы и генеративный ИИ",
]

LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
LINK_ENTRY_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
POINT_PATTERN = re.compile(r"^\| (?:Модуль [1-6]|Зачёт) \|.*\| (\d+) \|$", re.MULTILINE)
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$")
DECLARED_MAX_PATTERN = re.compile(r"\*\*Максимум:\s*(\d+)\s+бал", re.IGNORECASE)
KIM_MAX_PATTERN = re.compile(r"Максимум\s*[—–-]\s*(\d+)\s+бал", re.IGNORECASE)

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

TARGET_INDICATORS = [
    "LC-1.1",
    "BD-1.2",
    "BD-1.3",
    "BD-1.5",
    "ML-2.1",
    "ML-2.2",
    "ML-2.3",
]

INDICATOR_COMPETENCES = {
    "LC-1.1": "LC-1",
    "BD-1.2": "BD-1",
    "BD-1.3": "BD-1",
    "BD-1.5": "BD-1",
    "ML-2.1": "ML-2",
    "ML-2.2": "ML-2",
    "ML-2.3": "ML-2",
}

INDICATOR_THRESHOLDS = {
    "LC-1.1": "7 из 14",
    "BD-1.2": "9 из 18",
    "BD-1.3": "5 из 9",
    "BD-1.5": "4 из 8",
    "ML-2.1": "8 из 15",
    "ML-2.2": "8 из 15",
    "ML-2.3": "11 из 21",
}

INDICATOR_MINIMUMS = {
    "LC-1.1": 7,
    "BD-1.2": 9,
    "BD-1.3": 5,
    "BD-1.5": 4,
    "ML-2.1": 8,
    "ML-2.2": 8,
    "ML-2.3": 11,
}

MEASUREMENT_LINKS = {
    "КИМ-1": (
        "../M1-task-formulation/kim-01-project-brief.md",
        "../M1-task-formulation/rubric-01.md",
    ),
    "КИМ-2": (
        "../M2-data-understanding/kim-02-eda.md",
        "../M2-data-understanding/rubric-02.md",
    ),
    "КИМ-3": (
        "../M3-data-preparation/kim-03-data-preparation.md",
        "../M3-data-preparation/rubric-03.md",
    ),
    "КИМ-4": (
        "../M4-modeling/kim-04-modeling.md",
        "../M4-modeling/rubric-04.md",
    ),
    "КИМ-5": (
        "../M5-evaluation/kim-05-validation.md",
        "../M5-evaluation/rubric-05.md",
    ),
    "КИМ-6": (
        "../M6-analytical-product/kim-06-analytical-report.md",
        "../M6-analytical-product/rubric-06.md",
    ),
    "Защита": (
        "../Exam/README.md",
        "../Exam/README.md#7-оценивание-защиты",
    ),
}

MEASUREMENT_SYNC_FILES = [
    "README.md",
    "docs/README.md",
    "docs/fos.md",
    "docs/review-guide.md",
]

ROLE_TRAJECTORY_REQUIRED_SNIPPETS = [
    "промежуточный уровень С",
    "рекомендован уровень П",
    "могут уточняться с учётом образовательной программы",
    "3 ЗЕТ",
    "108 часов",
    "Дисциплина по углублённой статистике",
    "Практика",
    "НИРС",
    "Выпускная работа",
    "возможными, а не обязательными",
    "не включаются в 100-балльную модель курса",
    "BD-1.2",
    "BD-1.3",
    "BD-1.5",
    "Предполагаемые артефакты",
    "Возможная форма контроля",
]

ROLE_TRAJECTORY_SYNC_FILES = [
    "README.md",
    "docs/README.md",
    "docs/rpd.md",
    "docs/competency-model.md",
    "docs/semester-guide.md",
]


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not set(path.relative_to(ROOT).parts) & LOCAL_DIRECTORY_NAMES
    )


def check_required(errors: list[str]) -> None:
    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).exists():
            errors.append(f"missing required path: {relative}")
    for module, kim, rubric in MODULES:
        for relative in (f"{module}/README.md", f"{module}/{kim}", f"{module}/{rubric}"):
            if not (ROOT / relative).is_file():
                errors.append(f"missing module file: {relative}")
    for relative in SYNTHETIC_CASE_PATHS:
        if not (ROOT / relative).is_file():
            errors.append(f"missing synthetic case file: {relative}")


def check_markers(errors: list[str]) -> None:
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                errors.append(f"unresolved marker {marker!r}: {path.relative_to(ROOT)}")
        for pattern in FORBIDDEN_MARKER_PATTERNS:
            match = pattern.search(text)
            if match:
                errors.append(
                    f"unresolved template marker {match.group(0)!r}: "
                    f"{path.relative_to(ROOT)}"
                )


def github_heading_anchors(text: str) -> set[str]:
    """Return GitHub-style anchors for Markdown ATX headings."""

    anchors: set[str] = set()
    slug_counts: dict[str, int] = {}
    for line in text.splitlines():
        match = HEADING_PATTERN.match(line)
        if not match:
            continue
        heading = match.group(1).strip().rstrip("#").strip()
        heading = re.sub(r"<[^>]+>", "", heading)
        heading = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
        heading = re.sub(r"[`*_~]", "", heading).casefold()
        slug = "".join(
            character
            for character in heading
            if character.isalnum() or character in {" ", "-", "_"}
        )
        slug = re.sub(r"[\s-]+", "-", slug).strip("-")
        if not slug:
            continue
        duplicate_index = slug_counts.get(slug, 0)
        slug_counts[slug] = duplicate_index + 1
        anchors.add(slug if duplicate_index == 0 else f"{slug}-{duplicate_index}")
    return anchors


def check_links(errors: list[str]) -> None:
    anchors_by_path: dict[Path, set[str]] = {}
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, separator, raw_anchor = target.partition("#")
            file_part = unquote(file_part)
            raw_anchor = unquote(raw_anchor).casefold()
            resolved = (path.parent / file_part).resolve() if file_part else path.resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"link escapes repository: {path.relative_to(ROOT)} -> {target}")
                continue
            if not resolved.exists():
                errors.append(f"broken local link: {path.relative_to(ROOT)} -> {target}")
                continue
            if separator and raw_anchor and resolved.suffix.casefold() == ".md":
                if resolved not in anchors_by_path:
                    anchors_by_path[resolved] = github_heading_anchors(
                        resolved.read_text(encoding="utf-8")
                    )
                if raw_anchor not in anchors_by_path[resolved]:
                    errors.append(
                        f"broken Markdown anchor: {path.relative_to(ROOT)} -> {target}"
                    )


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


def parse_fos_matrix(errors: list[str]) -> dict[str, list[int]]:
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
    return found


def check_fos_matrix(errors: list[str]) -> None:
    found = parse_fos_matrix(errors)
    if found != FOS_MATRIX:
        errors.append(f"unexpected FOS matrix: {found}")

    if found:
        column_totals = [sum(row[index] for row in found.values()) for index in range(8)]
        if column_totals != [14, 18, 9, 8, 15, 15, 21, 100]:
            errors.append(f"unexpected FOS column totals: {column_totals}")


def markdown_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def check_rubrics(errors: list[str]) -> None:
    """Recalculate every module rubric and compare it with its KIM and FOS row."""

    for module_index, (module, kim_file, rubric_file) in enumerate(MODULES, start=1):
        rubric_path = ROOT / module / rubric_file
        kim_path = ROOT / module / kim_file
        if not rubric_path.exists() or not kim_path.exists():
            continue

        rubric_text = rubric_path.read_text(encoding="utf-8")
        lines = rubric_text.splitlines()
        header_index = next(
            (
                index
                for index, line in enumerate(lines)
                if line.startswith("|") and "Индикатор" in line
            ),
            None,
        )
        if header_index is None:
            errors.append(f"rubric has no indicator table: {rubric_path.relative_to(ROOT)}")
            continue

        header = markdown_table_cells(lines[header_index])
        points_column = next(
            (
                index
                for index, cell in enumerate(header)
                if cell.casefold() in {"максимум", "балл", "баллы"}
            ),
            None,
        )
        scale_values = [
            int(match.group(1))
            for cell in header
            if (match := re.search(r"(\d+)\s+бал", cell, re.IGNORECASE))
        ]
        row_scale_max = max(scale_values) if scale_values else None
        if points_column is None and row_scale_max is None:
            errors.append(
                f"rubric has no readable point scale: {rubric_path.relative_to(ROOT)}"
            )
            continue

        by_indicator: dict[str, int] = {}
        data_rows = 0
        for line in lines[header_index + 2 :]:
            if not line.startswith("|"):
                break
            cells = markdown_table_cells(line)
            if len(cells) != len(header):
                errors.append(
                    f"rubric row has {len(cells)} columns, expected {len(header)}: "
                    f"{rubric_path.relative_to(ROOT)}"
                )
                continue
            indicator = cells[0].strip("`")
            if indicator not in TARGET_INDICATORS:
                errors.append(
                    f"rubric contains unknown indicator {indicator!r}: "
                    f"{rubric_path.relative_to(ROOT)}"
                )
                continue
            if points_column is not None:
                raw_points = re.sub(r"[*_`]", "", cells[points_column])
                match = re.fullmatch(r"\d+", raw_points)
                if not match:
                    errors.append(
                        f"rubric has non-numeric maximum {cells[points_column]!r}: "
                        f"{rubric_path.relative_to(ROOT)}"
                    )
                    continue
                row_points = int(raw_points)
            else:
                row_points = int(row_scale_max)
            by_indicator[indicator] = by_indicator.get(indicator, 0) + row_points
            data_rows += 1

        total = sum(by_indicator.values())
        declared_match = DECLARED_MAX_PATTERN.search(rubric_text)
        if not declared_match:
            errors.append(f"rubric has no declared maximum: {rubric_path.relative_to(ROOT)}")
        elif int(declared_match.group(1)) != total:
            errors.append(
                f"rubric calculated maximum is {total}, declared "
                f"{declared_match.group(1)}: {rubric_path.relative_to(ROOT)}"
            )
        if data_rows == 0:
            errors.append(f"rubric has no criteria rows: {rubric_path.relative_to(ROOT)}")

        kim_name = f"КИМ-{module_index}"
        expected_row = FOS_MATRIX[kim_name]
        expected_by_indicator = {
            indicator: expected_row[index]
            for index, indicator in enumerate(TARGET_INDICATORS)
            if expected_row[index] > 0
        }
        if by_indicator != expected_by_indicator:
            errors.append(
                f"rubric distribution does not match docs/fos.md for {kim_name}: "
                f"{by_indicator} != {expected_by_indicator}"
            )
        if total != expected_row[-1]:
            errors.append(
                f"rubric total does not match docs/fos.md for {kim_name}: "
                f"{total} != {expected_row[-1]}"
            )

        kim_text = kim_path.read_text(encoding="utf-8")
        kim_match = KIM_MAX_PATTERN.search(kim_text)
        if not kim_match:
            errors.append(f"KIM has no declared maximum: {kim_path.relative_to(ROOT)}")
        elif int(kim_match.group(1)) != total:
            errors.append(
                f"KIM maximum does not match rubric for {kim_name}: "
                f"{kim_match.group(1)} != {total}"
            )


def parse_indicator_thresholds(
    path: Path,
    include_available_column: bool,
    errors: list[str],
) -> dict[str, tuple[int, int]]:
    found: dict[str, tuple[int, int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = markdown_table_cells(line)
        indicator = cells[0].strip("`") if cells else ""
        if indicator not in TARGET_INDICATORS:
            continue
        try:
            if include_available_column and len(cells) == 3:
                available = int(cells[1])
                minimum = int(cells[2])
            elif not include_available_column and len(cells) == 2:
                if "из" not in cells[1]:
                    continue
                match = re.fullmatch(r"(\d+)\s+из\s+(\d+)", cells[1])
                if not match:
                    raise ValueError
                minimum = int(match.group(1))
                available = int(match.group(2))
            else:
                raise ValueError
        except ValueError:
            errors.append(
                f"invalid threshold row for {indicator}: {path.relative_to(ROOT)}"
            )
            continue
        found[indicator] = (available, minimum)
    return found


def check_indicator_thresholds(errors: list[str]) -> None:
    fos_thresholds = parse_indicator_thresholds(
        ROOT / "docs/fos.md",
        include_available_column=True,
        errors=errors,
    )
    assessment_thresholds = parse_indicator_thresholds(
        ROOT / "docs/assessment-system.md",
        include_available_column=False,
        errors=errors,
    )
    available_totals = {
        indicator: sum(row[index] for row in FOS_MATRIX.values())
        for index, indicator in enumerate(TARGET_INDICATORS)
    }
    expected = {
        indicator: (available_totals[indicator], INDICATOR_MINIMUMS[indicator])
        for indicator in TARGET_INDICATORS
    }
    if fos_thresholds != expected:
        errors.append(f"indicator thresholds in docs/fos.md differ: {fos_thresholds}")
    if assessment_thresholds != expected:
        errors.append(
            "indicator thresholds in docs/assessment-system.md differ: "
            f"{assessment_thresholds}"
        )


def check_environment_files(errors: list[str]) -> None:
    lock_path = ROOT / "requirements-lock.txt"
    readable_path = ROOT / "requirements.txt"
    case_path = ROOT / "examples/synthetic-case/requirements.txt"
    if not all(path.exists() for path in (lock_path, readable_path, case_path)):
        return

    lock_text = lock_path.read_text(encoding="utf-8")
    if "autogenerated by uv" not in lock_text or "--universal --python-version 3.12" not in lock_text:
        errors.append("requirements-lock.txt is not a universal Python 3.12 uv lock")

    direct_packages = {
        "jupyterlab",
        "numpy",
        "pandas",
        "scipy",
        "statsmodels",
        "matplotlib",
        "seaborn",
        "scikit-learn",
    }
    locked_packages: set[str] = set()
    for line in lock_text.splitlines():
        if not line or line.startswith(("#", " ")):
            continue
        if "==" not in line:
            errors.append(f"unlocked requirement in requirements-lock.txt: {line}")
            continue
        locked_packages.add(line.split("==", 1)[0].strip().casefold())
    missing = sorted(direct_packages - locked_packages)
    if missing:
        errors.append(f"direct dependencies missing from requirements-lock.txt: {missing}")

    readable_text = readable_path.read_text(encoding="utf-8")
    for package in direct_packages:
        if not re.search(rf"^{re.escape(package)}[<>=]", readable_text, re.MULTILINE):
            errors.append(f"direct dependency missing from requirements.txt: {package}")
    case_text = case_path.read_text(encoding="utf-8")
    if "-r ../../requirements.txt" not in case_text or "==" in case_text:
        errors.append("synthetic case must reuse the readable root requirements.txt")


def check_measurement_model(errors: list[str]) -> None:
    path = ROOT / "docs/measurement-model.md"
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    rows: list[tuple[int, list[str]]] = []
    in_table = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("| Модуль или элемент |"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(not cell or set(cell) <= {":", "-"} for cell in cells):
            continue
        if len(cells) != 14:
            errors.append(f"measurement model row {line_number} has {len(cells)} columns, expected 14")
            continue
        rows.append((line_number, cells))

    if len(rows) != 22:
        errors.append(f"measurement model has {len(rows)} data rows, expected 22")

    measurement_matrix = {name: [0] * len(TARGET_INDICATORS) for name in FOS_MATRIX}
    seen_indicators: set[str] = set()
    seen_kims: set[str] = set()

    for line_number, cells in rows:
        competence = cells[2].strip("`")
        indicator = cells[3].strip("`")
        level = cells[4]
        descriptor = cells[5]
        artifact = cells[6]
        lesson_form = cells[7]
        control_form = cells[8]
        kim_cell = cells[9]
        rubric_cell = cells[10]
        points_cell = cells[11]
        threshold = cells[12]
        resources_cell = cells[13]

        if indicator not in INDICATOR_COMPETENCES:
            errors.append(f"measurement model row {line_number} has unknown indicator: {indicator}")
            continue
        seen_indicators.add(indicator)

        if competence != INDICATOR_COMPETENCES[indicator]:
            errors.append(
                f"measurement model row {line_number} maps {indicator} to {competence}, "
                f"expected {INDICATOR_COMPETENCES[indicator]}"
            )
        if level != "С":
            errors.append(f"measurement model row {line_number} has level {level!r}, expected 'С'")
        if threshold != INDICATOR_THRESHOLDS[indicator]:
            errors.append(
                f"measurement model row {line_number} has threshold {threshold!r} for {indicator}, "
                f"expected {INDICATOR_THRESHOLDS[indicator]!r}"
            )
        for field_name, value in (
            ("element", cells[0]),
            ("thematic content", cells[1]),
            ("descriptor", descriptor),
            ("artifact", artifact),
            ("lesson form", lesson_form),
            ("control form", control_form),
        ):
            if not value:
                errors.append(f"measurement model row {line_number} has empty {field_name}")

        kim_match = LINK_ENTRY_PATTERN.fullmatch(kim_cell)
        rubric_match = LINK_ENTRY_PATTERN.fullmatch(rubric_cell)
        if not kim_match:
            errors.append(f"measurement model row {line_number} has unlinked KIM")
            continue
        if not rubric_match:
            errors.append(f"measurement model row {line_number} has unlinked rubric")
            continue

        kim_name = kim_match.group(1)
        if kim_name.casefold() == "защита":
            kim_name = "Защита"
        if kim_name not in MEASUREMENT_LINKS:
            errors.append(f"measurement model row {line_number} has unknown KIM: {kim_name}")
            continue
        seen_kims.add(kim_name)

        expected_kim_link, expected_rubric_link = MEASUREMENT_LINKS[kim_name]
        if kim_match.group(2) != expected_kim_link:
            errors.append(f"measurement model row {line_number} has unexpected KIM link for {kim_name}")
        if rubric_match.group(2) != expected_rubric_link:
            errors.append(f"measurement model row {line_number} has unexpected rubric link for {kim_name}")

        resource_matches = list(LINK_ENTRY_PATTERN.finditer(resources_cell))
        unlinked_resource_text = LINK_ENTRY_PATTERN.sub("", resources_cell).strip(" ,;")
        if not resource_matches or unlinked_resource_text:
            errors.append(f"measurement model row {line_number} has unlinked resource text")

        try:
            points = int(points_cell)
        except ValueError:
            errors.append(f"measurement model row {line_number} has non-numeric points: {points_cell!r}")
            continue
        if points <= 0:
            errors.append(f"measurement model row {line_number} has non-positive points: {points}")
            continue

        indicator_index = TARGET_INDICATORS.index(indicator)
        measurement_matrix[kim_name][indicator_index] += points

    if seen_indicators != set(TARGET_INDICATORS):
        errors.append(f"measurement model indicator set differs: {sorted(seen_indicators)}")
    if seen_kims != set(FOS_MATRIX):
        errors.append(f"measurement model KIM set differs: {sorted(seen_kims)}")

    fos_matrix = parse_fos_matrix(errors)
    measurement_with_totals = {
        name: values + [sum(values)]
        for name, values in measurement_matrix.items()
    }
    if measurement_with_totals != fos_matrix:
        errors.append(
            "measurement model point matrix does not match docs/fos.md: "
            f"{measurement_with_totals}"
        )

    if measurement_with_totals:
        indicator_totals = [
            sum(row[index] for row in measurement_with_totals.values())
            for index in range(len(TARGET_INDICATORS))
        ]
        fos_indicator_totals = [
            sum(row[index] for row in fos_matrix.values())
            for index in range(len(TARGET_INDICATORS))
        ]
        if indicator_totals != fos_indicator_totals:
            errors.append(
                "measurement model indicator totals do not match docs/fos.md: "
                f"{indicator_totals} != {fos_indicator_totals}"
            )
        if sum(row[-1] for row in measurement_with_totals.values()) != 100:
            errors.append("measurement model points do not sum to 100")

    for relative in MEASUREMENT_SYNC_FILES:
        linked_path = ROOT / relative
        if linked_path.exists() and "measurement-model.md" not in linked_path.read_text(encoding="utf-8"):
            errors.append(f"measurement model is not linked from: {relative}")


def check_role_trajectory(errors: list[str]) -> None:
    trajectory_path = ROOT / "docs/role-trajectory.md"
    if not trajectory_path.exists():
        return

    trajectory_text = trajectory_path.read_text(encoding="utf-8")
    for snippet in ROLE_TRAJECTORY_REQUIRED_SNIPPETS:
        if snippet not in trajectory_text:
            errors.append(f"role trajectory is missing key statement: {snippet!r}")

    for relative in ROLE_TRAJECTORY_SYNC_FILES:
        path = ROOT / relative
        if path.exists() and "role-trajectory.md" not in path.read_text(encoding="utf-8"):
            errors.append(f"role trajectory is not linked from: {relative}")


def check_synthetic_case(errors: list[str]) -> None:
    case_root = ROOT / "examples/synthetic-case"
    data_path = case_root / "data/subscriber_retention.csv"
    manifest_path = case_root / "data/generation-manifest.json"
    schema_path = case_root / "data/schema.json"
    ranges_path = case_root / "teacher/expected_metric_ranges.json"
    metrics_path = case_root / "teacher/reference-output/baseline-metrics.json"
    log_path = case_root / "teacher/reference-output/experiment-log.csv"
    notebook_path = case_root / "student/starter.ipynb"

    required_files = [
        data_path,
        manifest_path,
        schema_path,
        ranges_path,
        metrics_path,
        log_path,
        notebook_path,
    ]
    if not all(path.exists() for path in required_files):
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    if manifest.get("sha256") != digest:
        errors.append("synthetic case CSV checksum differs from generation manifest")
    parameters = manifest.get("parameters", {})
    if parameters.get("seed") != 20260728:
        errors.append(f"unexpected synthetic case seed: {parameters.get('seed')}")
    if manifest.get("generator_version") != "1.0.0":
        errors.append(f"unexpected synthetic generator version: {manifest.get('generator_version')}")

    with data_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        data_rows = list(reader)
    if len(data_rows) != manifest.get("rows_with_duplicates"):
        errors.append(
            "synthetic case row count differs from manifest: "
            f"{len(data_rows)} != {manifest.get('rows_with_duplicates')}"
        )

    expected_fields = {
        "row_id",
        "customer_id",
        "snapshot_date",
        "region",
        "plan_type",
        "acquisition_channel",
        "autopay",
        "tenure_months",
        "monthly_fee",
        "usage_hours_30d",
        "usage_change_90d",
        "support_tickets_90d",
        "late_payments_6m",
        "satisfaction_score",
        "days_since_last_login",
        "network_incidents_30d",
        "leaked_churn_score",
        "retention_offer_result_14d",
        "churn_30d",
    }
    if set(reader.fieldnames or []) != expected_fields:
        errors.append(f"unexpected synthetic case CSV fields: {reader.fieldnames}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if set(schema) != expected_fields:
        errors.append(f"synthetic case schema fields differ: {sorted(schema)}")
    for field in ("leaked_churn_score", "retention_offer_result_14d"):
        if schema.get(field, {}).get("available_at_decision") is not False:
            errors.append(f"synthetic case field must be unavailable at decision: {field}")
    if schema.get("leaked_churn_score", {}).get("role") != "intentional_leakage":
        errors.append("leaked_churn_score is not marked as intentional leakage")
    if schema.get("retention_offer_result_14d", {}).get("role") != "post_decision_feature":
        errors.append("retention_offer_result_14d is not marked as post-decision")

    range_payload = json.loads(ranges_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    expected_metric_names = {
        "roc_auc",
        "average_precision",
        "f1_at_0_50",
        "precision_at_top_15pct",
        "recall_at_top_15pct",
    }
    ranges = range_payload.get("ranges", {})
    if set(ranges) != expected_metric_names:
        errors.append(f"unexpected synthetic metric range set: {sorted(ranges)}")
    for name, limits in ranges.items():
        if not isinstance(limits, list) or len(limits) != 2 or limits[0] >= limits[1]:
            errors.append(f"invalid metric range for {name}: {limits}")
            continue
        value = metrics.get(name)
        if not isinstance(value, (int, float)) or not limits[0] <= value <= limits[1]:
            errors.append(f"reference metric {name}={value} is outside {limits}")
    if set(metrics.get("excluded_fields", [])) != {
        "leaked_churn_score",
        "retention_offer_result_14d",
    }:
        errors.append("reference baseline does not declare both forbidden fields")

    with log_path.open(encoding="utf-8", newline="") as source:
        log_rows = list(csv.DictReader(source))
    if len(log_rows) != 1:
        errors.append(f"reference experiment log has {len(log_rows)} rows, expected 1")
    elif log_rows[0].get("run_id") != metrics.get("run_id"):
        errors.append("reference experiment log run_id differs from baseline metrics")

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    if notebook.get("nbformat") != 4:
        errors.append("starter notebook must use nbformat 4")
    notebook_text = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])
    )
    if "TODO" not in notebook_text:
        errors.append("starter notebook has no student TODO markers")
    if "LogisticRegression" in notebook_text or "teacher/baseline" in notebook_text:
        errors.append("starter notebook exposes the teacher baseline")
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            if cell.get("execution_count") is not None or cell.get("outputs"):
                errors.append("starter notebook contains executed code or saved outputs")
                break

    generation_code = (case_root / "generate_data.py").read_text(encoding="utf-8")
    preparation_code = (case_root / "src/data_preparation.py").read_text(encoding="utf-8")
    variant_code = (case_root / "generate_variants.py").read_text(encoding="utf-8")
    tests_code = (case_root / "tests/test_case.py").read_text(encoding="utf-8")
    for snippet in (
        "DEFAULT_SEED = 20260728",
        "leaked_churn_score",
        "retention_offer_result_14d",
        "duplicate_rate",
        "outlier_rate",
    ):
        if snippet not in generation_code:
            errors.append(f"synthetic generator is missing: {snippet}")
    for field in ("leaked_churn_score", "retention_offer_result_14d"):
        if field not in preparation_code:
            errors.append(f"data preparation does not exclude field: {field}")
    if "variant_config" not in variant_code or "base_seed + 1009 * variant_id" not in variant_code:
        errors.append("variant generator does not derive reproducible variant seeds")
    for test_name in (
        "test_fixed_seed_is_reproducible",
        "test_schema_and_types",
        "test_preprocessor_uses_only_safe_fields",
        "test_group_split_does_not_share_customers",
        "test_baseline_is_reproducible",
        "test_default_dataset_rebuilds_byte_for_byte",
    ):
        if test_name not in tests_code:
            errors.append(f"synthetic case test is missing: {test_name}")

    for relative in (
        "README.md",
        "resources/README.md",
        "resources/datasets/README.md",
        "resources/problem-banks/README.md",
        "resources/benchmarks/README.md",
        "Project/README.md",
        "docs/review-guide.md",
        "docs/quality-checklist.md",
        "methodical-guidelines/README.md",
        "methodical-guidelines/students/README.md",
        "methodical-guidelines/teachers-resources/README.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "synthetic-case" not in text:
            errors.append(f"synthetic case is not linked from: {relative}")


def check_files(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or set(path.relative_to(ROOT).parts) & LOCAL_DIRECTORY_NAMES
        ):
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
    check_rubrics(errors)
    check_indicator_thresholds(errors)
    check_measurement_model(errors)
    check_role_trajectory(errors)
    check_synthetic_case(errors)
    check_environment_files(errors)
    check_files(errors)

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Repository validation passed: {len(markdown_files())} Markdown files checked.")
    print(
        "Checked: required files, links and anchors, template markers, six rubrics, "
        "KIM/FOS points, indicator thresholds, environment files, and synthetic case."
    )
    print("Manual publication checks remain: team identities, OPOP metadata, and license approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
