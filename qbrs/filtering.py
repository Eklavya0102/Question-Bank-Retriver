"""Basic filtering of questions by Unit, CO and maximum Bloom level."""

from __future__ import annotations

from typing import Sequence

from .models import BasicQuery, Question


def matches_query(question: Question, query: BasicQuery) -> bool:
    """True if the question satisfies unit, CO and max Bloom level."""
    return (
        question.unit == query.unit
        and question.co == query.co
        and question.bloom_level <= query.max_bloom
    )


def filter_questions(
    questions: Sequence[Question], query: BasicQuery
) -> list[Question]:
    """Return matching questions, preserving their original input order."""
    return [q for q in questions if matches_query(q, query)]


def format_result(matches: Sequence[Question]) -> str:
    """Space-separated question IDs; an empty string if nothing matched."""
    return " ".join(q.question_id for q in matches)
