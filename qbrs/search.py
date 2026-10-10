
from __future__ import annotations

from typing import Optional, cast

from .bitset_index import BitsetIndex
from .models import Difficulty, Question
from .query_ast import And, Attribute, Condition, Node, Not, Or
from .query_parser import parse_query


def _condition_bits(condition: Condition, index: BitsetIndex) -> int:
    attribute, value = condition.attribute, condition.value
    if attribute is Attribute.UNIT:
        return index.unit(cast(int, value))
    if attribute is Attribute.CO:
        return index.co(cast(str, value))
    if attribute is Attribute.BLOOM:
        return index.bloom(cast(int, value))
    if attribute is Attribute.MAXBLOOM:
        return index.bloom_at_most(cast(int, value))
    if attribute is Attribute.DIFFICULTY:
        return index.difficulty(cast(Difficulty, value))
    raise ValueError(f"Unsupported attribute: {attribute!r}")


def evaluate(node: Node, index: BitsetIndex) -> int:
    if isinstance(node, Condition):
        return _condition_bits(node, index)
    if isinstance(node, Not):
        return index.complement(evaluate(node.operand, index))
    if isinstance(node, And):
        result = index.all_mask
        for operand in node.operands:
            result &= evaluate(operand, index)
            if not result:
                break  # nothing left to intersect with
        return result
    if isinstance(node, Or):
        result = 0
        for operand in node.operands:
            result |= evaluate(operand, index)
        return result
    raise TypeError(f"Unknown query node: {node!r}")


def run_query(
    index: BitsetIndex, query_text: str, line_no: Optional[int] = None
) -> list[Question]:
    """Parse ``query_text`` and return matching questions in input order."""
    return index.questions_for(evaluate(parse_query(query_text, line_no), index))
