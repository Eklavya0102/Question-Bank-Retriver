"""Abstract syntax tree for Boolean queries.

AND and OR nodes hold a tuple of operands, so a long chain such as
``a AND b AND c AND ...`` stays one flat node instead of a deep tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union

from .models import Difficulty


class Attribute(str, Enum):
    """Attributes that can appear in a query condition."""

    UNIT = "unit"
    CO = "co"
    BLOOM = "bloom"  # exactly this Bloom level
    MAXBLOOM = "maxbloom"  # this Bloom level or any lower one
    DIFFICULTY = "difficulty"


ConditionValue = Union[int, str, Difficulty]


@dataclass(frozen=True)
class Condition:
    """A single ``attribute=value`` test, e.g. ``unit=1`` or ``maxbloom=K3``.

    Values are already validated and normalised: Unit and Bloom levels are
    ints (K3 -> 3), CO is upper-case text, Difficulty is a ``Difficulty``.
    """

    attribute: Attribute
    value: ConditionValue


@dataclass(frozen=True)
class Not:
    operand: Node


@dataclass(frozen=True)
class And:
    operands: tuple[Node, ...]


@dataclass(frozen=True)
class Or:
    operands: tuple[Node, ...]


Node = Union[Condition, Not, And, Or]
