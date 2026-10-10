"""Reading and validating input (question records and the basic query)."""

from __future__ import annotations

import re
from typing import Iterable, TextIO

from .errors import InputError
from .models import (
    MAX_BLOOM_LEVEL,
    MIN_BLOOM_LEVEL,
    BasicQuery,
    Difficulty,
    Question,
)

_CO_PATTERN = re.compile(r"^CO[1-9][0-9]*$")
_BLOOM_PATTERN = re.compile(r"^K([1-6])$")
_QUERY_KEYS = ("unit", "co", "maxbloom")


# --------------------------------------------------------------------------
# Field-level parsing / validation
# --------------------------------------------------------------------------
def parse_positive_int(text: str, field_name: str) -> int:
    """Parse a positive integer (>= 1), e.g. a Unit number."""
    if not text.isascii() or not text.isdigit():
        raise InputError(
            f"Invalid {field_name} '{text}': expected a positive integer."
        )
    value = int(text)
    if value < 1:
        raise InputError(
            f"Invalid {field_name} '{text}': must be 1 or greater."
        )
    return value


def parse_co(text: str) -> str:
    """Validate a course outcome such as CO1 and return it upper-cased."""
    normalised = text.upper()
    if not _CO_PATTERN.match(normalised):
        raise InputError(
            f"Invalid CO '{text}': expected the form CO<number>, e.g. CO1."
        )
    return normalised


def parse_bloom_level(text: str) -> int:
    """Validate a Bloom level K1..K6 and return its numeric part."""
    match = _BLOOM_PATTERN.match(text.upper())
    if not match:
        raise InputError(
            f"Invalid Bloom level '{text}': expected K{MIN_BLOOM_LEVEL} "
            f"to K{MAX_BLOOM_LEVEL}."
        )
    return int(match.group(1))


def parse_difficulty(text: str) -> Difficulty:
    """Validate a difficulty value (EASY, MEDIUM or HARD)."""
    try:
        return Difficulty(text.upper())
    except ValueError:
        allowed = ", ".join(d.value for d in Difficulty)
        raise InputError(
            f"Invalid difficulty '{text}': expected one of {allowed}."
        ) from None


# --------------------------------------------------------------------------
# Record / query parsing
# --------------------------------------------------------------------------
def parse_question_record(line: str, line_no: int) -> Question:
    """Parse `QuestionID Unit CO BloomLevel Difficulty` into a Question."""
    parts = line.split()
    if len(parts) != 5:
        raise InputError(
            f"Line {line_no}: expected 5 fields "
            f"(QuestionID Unit CO BloomLevel Difficulty) but found "
            f"{len(parts)}: '{line.strip()}'."
        )
    question_id, unit, co, bloom, difficulty = parts
    try:
        return Question(
            question_id=question_id,
            unit=parse_positive_int(unit, "Unit"),
            co=parse_co(co),
            bloom_level=parse_bloom_level(bloom),
            difficulty=parse_difficulty(difficulty),
        )
    except InputError as exc:
        raise InputError(f"Line {line_no}: {exc}") from None


def parse_basic_query(line: str, line_no: int) -> BasicQuery:
    """Parse `FIND unit=<n> co=<CO> maxbloom=<K>` into a BasicQuery."""
    parts = line.split()
    if not parts or parts[0].upper() != "FIND":
        raise InputError(
            f"Line {line_no}: query must start with FIND, e.g. "
            f"'FIND unit=1 co=CO1 maxbloom=K3'."
        )

    values: dict[str, str] = {}
    for token in parts[1:]:
        key, sep, value = token.partition("=")
        key = key.lower()
        if not sep or not value:
            raise InputError(
                f"Line {line_no}: malformed query term '{token}': "
                f"expected key=value."
            )
        if key not in _QUERY_KEYS:
            raise InputError(
                f"Line {line_no}: unknown query field '{key}': "
                f"expected unit, co or maxbloom."
            )
        if key in values:
            raise InputError(
                f"Line {line_no}: query field '{key}' given more than once."
            )
        values[key] = value

    missing = [k for k in _QUERY_KEYS if k not in values]
    if missing:
        raise InputError(
            f"Line {line_no}: query is missing: {', '.join(missing)}."
        )

    try:
        return BasicQuery(
            unit=parse_positive_int(values["unit"], "unit"),
            co=parse_co(values["co"]),
            max_bloom=parse_bloom_level(values["maxbloom"]),
        )
    except InputError as exc:
        raise InputError(f"Line {line_no}: {exc}") from None


# --------------------------------------------------------------------------
# Whole-input reading
# --------------------------------------------------------------------------
def _numbered_non_blank_lines(stream: Iterable[str]) -> list[tuple[int, str]]:
    """Return (original line number, stripped text) for non-blank lines."""
    return [
        (number, text.strip())
        for number, text in enumerate(stream, start=1)
        if text.strip()
    ]


def read_dataset(stream: TextIO) -> tuple[list[Question], str, int]:
    """Read the question count, the question records and the raw query line.

    Returns ``(questions, query_text, query_line_number)``. The query text is
    not parsed here, so any query syntax can be layered on top.

    Blank lines are ignored. Raises InputError with a clear message if the
    input is incomplete, has extra lines, or any question record is invalid.
    """
    lines = _numbered_non_blank_lines(stream)
    if not lines:
        raise InputError("Input is empty: expected the number of questions.")

    count_line_no, count_text = lines[0]
    if not count_text.isascii() or not count_text.isdigit():
        raise InputError(
            f"Line {count_line_no}: the first line must be the number of "
            f"questions (a non-negative integer), got '{count_text}'."
        )
    n = int(count_text)

    # n question records + 1 query line follow the count line.
    available = len(lines) - 1
    if available < n:
        raise InputError(
            f"Expected {n} question record(s) but found only {available} "
            f"line(s) after the count."
        )
    if available == n:
        raise InputError(
            f"Missing query line: expected a FIND query after the "
            f"{n} question record(s)."
        )
    if available > n + 1:
        extra_no = lines[n + 2][0]
        raise InputError(
            f"Line {extra_no}: unexpected extra input after the query line."
        )

    questions: list[Question] = []
    seen_ids: dict[str, int] = {}
    for line_no, text in lines[1 : n + 1]:
        question = parse_question_record(text, line_no)
        if question.question_id in seen_ids:
            raise InputError(
                f"Line {line_no}: duplicate QuestionID "
                f"'{question.question_id}' (first used on line "
                f"{seen_ids[question.question_id]})."
            )
        seen_ids[question.question_id] = line_no
        questions.append(question)

    query_line_no, query_text = lines[n + 1]
    return questions, query_text, query_line_no


def read_input(stream: TextIO) -> tuple[list[Question], BasicQuery]:
    """Module 1 API: read the dataset and parse the basic FIND query.

    Only accepts the original `FIND unit=<n> co=<CO> maxbloom=<K>` form.
    """
    questions, query_text, query_line_no = read_dataset(stream)
    return questions, parse_basic_query(query_text, query_line_no)
