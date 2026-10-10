"""Boolean query parser (tokenizer + recursive descent).

Grammar
-------
    query      := "FIND" or_expr
    or_expr    := and_expr ( "OR" and_expr )*
    and_expr   := not_expr ( "AND" not_expr | condition )*
    not_expr   := "NOT" not_expr | primary
    primary    := "(" or_expr ")" | condition
    condition  := attribute "=" value

Operator precedence (highest binds tightest)
--------------------------------------------
    1. Parentheses
    2. NOT
    3. AND
    4. OR

So ``unit=1 OR unit=2 AND co=CO1`` means ``unit=1 OR (unit=2 AND co=CO1)``
and ``NOT unit=1 AND co=CO1`` means ``(NOT unit=1) AND co=CO1``.

Implicit AND (original syntax)
------------------------------
Two conditions written side by side are joined with AND, which keeps the
original form ``FIND unit=1 co=CO1 maxbloom=K3`` working. It has the same
precedence as an explicit AND. The AND keyword may only be left out before a
condition: before ``NOT`` or ``(`` it must be written out.

Attributes
----------
    unit=<n>              Unit number (positive integer)
    co=CO<n>              Course outcome, e.g. CO1
    bloom=K<1-6>          Bloom level exactly equal to K<n>
    maxbloom=K<1-6>       Bloom level K1 up to and including K<n>
    difficulty=<level>    EASY, MEDIUM or HARD

Keywords, attribute names and values are case-insensitive. Whitespace around
``=`` and parentheses is optional.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .errors import InputError
from .input_handler import (
    parse_bloom_level,
    parse_co,
    parse_difficulty,
    parse_positive_int,
)
from .query_ast import And, Attribute, Condition, ConditionValue, Node, Not, Or

MAX_NESTING_DEPTH = 100

_TOKEN_RE = re.compile(r"[()=]|[^\s()=]+")
_KEYWORDS = frozenset({"AND", "OR", "NOT"})
_ATTRIBUTE_NAMES = ", ".join(a.value for a in Attribute)

_LPAREN = "LPAREN"
_RPAREN = "RPAREN"
_EQUALS = "EQUALS"
_WORD = "WORD"
_END = "END"


class QueryParseError(InputError):
    """A query is malformed. ``column`` is 1-based within the query line."""

    def __init__(
        self, message: str, column: int, line_no: Optional[int] = None
    ) -> None:
        where = f"Line {line_no}, column {column}" if line_no else f"Column {column}"
        super().__init__(f"{where}: {message}")
        self.message = message
        self.column = column
        self.line_no = line_no


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    column: int  # 1-based

    @property
    def keyword(self) -> Optional[str]:
        """Upper-case AND / OR / NOT if this token is that keyword."""
        if self.kind == _WORD and self.text.upper() in _KEYWORDS:
            return self.text.upper()
        return None

    @property
    def is_plain_word(self) -> bool:
        """A word that is not a keyword (an attribute name or a value)."""
        return self.kind == _WORD and self.text.upper() not in _KEYWORDS


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    for match in _TOKEN_RE.finditer(text):
        piece = match.group()
        if piece == "(":
            kind = _LPAREN
        elif piece == ")":
            kind = _RPAREN
        elif piece == "=":
            kind = _EQUALS
        else:
            kind = _WORD
        tokens.append(_Token(kind, piece, match.start() + 1))
    return tokens


class _Parser:
    def __init__(self, text: str, line_no: Optional[int]) -> None:
        self._line_no = line_no
        self._tokens = _tokenize(text)
        self._end = _Token(_END, "", len(text.rstrip()) + 1)
        self._pos = 0
        self._depth = 0

    # -- helpers --------------------------------------------------------
    def _error(self, message: str, column: int) -> QueryParseError:
        return QueryParseError(message, column, self._line_no)

    def _peek(self) -> _Token:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else self._end

    def _advance(self) -> _Token:
        token = self._peek()
        if token.kind != _END:
            self._pos += 1
        return token

    def _descend(self, column: int) -> None:
        self._depth += 1
        if self._depth > MAX_NESTING_DEPTH:
            raise self._error(
                f"Query is nested too deeply (limit is {MAX_NESTING_DEPTH} "
                f"levels of NOT / parentheses).",
                column,
            )

    # -- grammar --------------------------------------------------------
    def parse(self) -> Node:
        first = self._peek()
        if first.kind != _WORD or first.text.upper() != "FIND":
            raise self._error(
                "Query must start with FIND, e.g. 'FIND unit=1 AND co=CO1'.",
                first.column,
            )
        self._advance()

        node = self._parse_or()

        leftover = self._peek()
        if leftover.kind == _RPAREN:
            raise self._error(
                "Unmatched ')': there is no '(' to close.", leftover.column
            )
        if leftover.kind != _END:
            raise self._error(
                f"Unexpected '{leftover.text}': expected AND, OR or the end "
                f"of the query.",
                leftover.column,
            )
        return node

    def _parse_or(self) -> Node:
        operands = [self._parse_and()]
        while self._peek().keyword == "OR":
            self._advance()
            operands.append(self._parse_and())
        return operands[0] if len(operands) == 1 else Or(tuple(operands))

    def _parse_and(self) -> Node:
        operands = [self._parse_not()]
        while True:
            token = self._peek()
            if token.keyword == "AND":
                self._advance()
                operands.append(self._parse_not())
            elif token.is_plain_word:
                # Original syntax: adjacent conditions mean AND.
                operands.append(self._parse_condition())
            elif token.keyword == "NOT" or token.kind == _LPAREN:
                raise self._error(
                    f"Missing AND or OR before '{token.text}'.", token.column
                )
            else:
                break
        return operands[0] if len(operands) == 1 else And(tuple(operands))

    def _parse_not(self) -> Node:
        token = self._peek()
        if token.keyword == "NOT":
            self._advance()
            self._descend(token.column)
            operand = self._parse_not()
            self._depth -= 1
            return Not(operand)
        return self._parse_primary()

    def _parse_primary(self) -> Node:
        token = self._peek()
        if token.kind == _LPAREN:
            return self._parse_group()
        if token.is_plain_word:
            return self._parse_condition()

        expected = "a condition (e.g. unit=1), NOT or '('"
        if token.kind == _END:
            previous = self._tokens[self._pos - 1].text if self._pos else "FIND"
            raise self._error(
                f"Incomplete query: expected {expected} after '{previous}', "
                f"but the query ended.",
                token.column,
            )
        raise self._error(
            f"Unexpected '{token.text}': expected {expected}.", token.column
        )

    def _parse_group(self) -> Node:
        opening = self._advance()
        self._descend(opening.column)
        if self._peek().kind == _RPAREN:
            raise self._error(
                "Empty parentheses: expected a condition between '(' and ')'.",
                opening.column,
            )
        node = self._parse_or()

        closing = self._peek()
        if closing.kind == _END:
            raise self._error(
                "Unmatched '(': there is no matching ')'.", opening.column
            )
        if closing.kind != _RPAREN:
            raise self._error(
                f"Unexpected '{closing.text}': expected ')' to close the '(' "
                f"opened at column {opening.column}.",
                closing.column,
            )
        self._advance()
        self._depth -= 1
        return node

    def _parse_condition(self) -> Condition:
        name_token = self._advance()
        name = name_token.text
        try:
            attribute = Attribute(name.lower())
        except ValueError:
            if re.search(r"[<>!~]", name):
                message = (
                    f"Unsupported operator in '{name}': only '=' is supported, "
                    f"e.g. unit=1."
                )
            else:
                message = (
                    f"Unknown attribute '{name}': expected one of "
                    f"{_ATTRIBUTE_NAMES}."
                )
            raise self._error(message, name_token.column) from None

        equals = self._peek()
        if equals.kind != _EQUALS:
            if equals.kind == _END:
                message = (
                    f"Incomplete condition: expected '=' and a value after "
                    f"'{name}', but the query ended."
                )
            else:
                message = f"Expected '=' after '{name}' but found '{equals.text}'."
            raise self._error(message, equals.column)
        self._advance()

        value_token = self._peek()
        if not value_token.is_plain_word:
            if value_token.kind == _END:
                message = (
                    f"Incomplete condition: expected a value after '{name}=' "
                    f"but the query ended."
                )
            else:
                message = (
                    f"Expected a value after '{name}=' but found "
                    f"'{value_token.text}'."
                )
            raise self._error(message, value_token.column)
        self._advance()
        return Condition(attribute, self._convert(attribute, value_token))

    def _convert(self, attribute: Attribute, token: _Token) -> ConditionValue:
        """Validate and normalise a condition value using Module 1 rules."""
        try:
            if attribute is Attribute.UNIT:
                return parse_positive_int(token.text, "unit")
            if attribute is Attribute.CO:
                return parse_co(token.text)
            if attribute in (Attribute.BLOOM, Attribute.MAXBLOOM):
                return parse_bloom_level(token.text)
            return parse_difficulty(token.text)
        except InputError as exc:
            raise self._error(str(exc), token.column) from None


def parse_query(text: str, line_no: Optional[int] = None) -> Node:
    """Parse a query line (including the leading FIND) into an AST.

    Raises QueryParseError (an InputError) with a 1-based column for any
    malformed query. ``line_no`` is only used to label error messages.
    """
    return _Parser(text, line_no).parse()
