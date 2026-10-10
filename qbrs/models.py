"""Data models for questions and search queries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MIN_BLOOM_LEVEL = 1
MAX_BLOOM_LEVEL = 6


class Difficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


@dataclass(frozen=True)
class Question:
    """A single question record from the bank."""

    question_id: str
    unit: int
    co: str  # normalised upper-case, e.g. "CO1"
    bloom_level: int  # 1..6 (K1..K6)
    difficulty: Difficulty


@dataclass(frozen=True)
class BasicQuery:
    """A parsed `FIND unit=<n> co=<CO> maxbloom=<K>` query."""

    unit: int
    co: str  # normalised upper-case, e.g. "CO1"
    max_bloom: int  # 1..6 (K1..K6)
