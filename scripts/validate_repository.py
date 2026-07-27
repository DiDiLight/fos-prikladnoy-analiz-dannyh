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
LINK_ENTRY_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
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
    check_measurement_model(errors)
    check_role_trajectory(errors)
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
