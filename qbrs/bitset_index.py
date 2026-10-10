
from __future__ import annotations

from typing import Iterable, Sequence

from .models import MAX_BLOOM_LEVEL, MIN_BLOOM_LEVEL, Difficulty, Question


def _bits_from_positions(positions: Iterable[int], size: int) -> int:
    """Build a bitset with the given bit positions set.

    Fills a bytearray and converts once, which is linear in ``size`` instead
    of creating a large integer for every position.
    """
    buffer = bytearray((size + 7) // 8)
    for position in positions:
        buffer[position >> 3] |= 1 << (position & 7)
    return int.from_bytes(buffer, "little")


class BitsetIndex:
    """One bitset per attribute value for a fixed list of questions."""

    def __init__(self, questions: Sequence[Question]) -> None:
        self._questions: tuple[Question, ...] = tuple(questions)
        self._size = len(self._questions)
        self._all_mask = (1 << self._size) - 1

        units: dict[int, list[int]] = {}
        cos: dict[str, list[int]] = {}
        blooms: dict[int, list[int]] = {}
        difficulties: dict[Difficulty, list[int]] = {}
        for position, question in enumerate(self._questions):
            units.setdefault(question.unit, []).append(position)
            cos.setdefault(question.co, []).append(position)
            blooms.setdefault(question.bloom_level, []).append(position)
            difficulties.setdefault(question.difficulty, []).append(position)

        size = self._size
        self._by_unit = {k: _bits_from_positions(v, size) for k, v in units.items()}
        self._by_co = {k: _bits_from_positions(v, size) for k, v in cos.items()}
        self._by_bloom = {k: _bits_from_positions(v, size) for k, v in blooms.items()}
        self._by_difficulty = {
            k: _bits_from_positions(v, size) for k, v in difficulties.items()
        }

        # Cumulative Bloom bitsets: entry k holds K1 | K2 | ... | Kk, so a
        # "maxbloom=Kk" query is a single lookup. Index 0 is unused.
        at_most = [0] * (MAX_BLOOM_LEVEL + 1)
        running = 0
        for level in range(MIN_BLOOM_LEVEL, MAX_BLOOM_LEVEL + 1):
            running |= self._by_bloom.get(level, 0)
            at_most[level] = running
        self._bloom_at_most = at_most

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return self._size

    @property
    def all_mask(self) -> int:
        """Bitset with a 1 for every valid question position."""
        return self._all_mask

    # ------------------------------------------------------------------
    # Attribute lookups (a value nobody has gives the empty bitset, 0)
    # ------------------------------------------------------------------
    def unit(self, unit: int) -> int:
        return self._by_unit.get(unit, 0)

    def co(self, co: str) -> int:
        return self._by_co.get(co, 0)

    def bloom(self, level: int) -> int:
        """Questions whose Bloom level is exactly ``level``."""
        return self._by_bloom.get(level, 0)

    def bloom_at_most(self, level: int) -> int:
        """Questions whose Bloom level is K1 .. K``level`` (inclusive)."""
        if not MIN_BLOOM_LEVEL <= level <= MAX_BLOOM_LEVEL:
            raise ValueError(
                f"Bloom level must be between {MIN_BLOOM_LEVEL} and "
                f"{MAX_BLOOM_LEVEL}, got {level}."
            )
        return self._bloom_at_most[level]

    def difficulty(self, difficulty: Difficulty) -> int:
        return self._by_difficulty.get(difficulty, 0)

    # ------------------------------------------------------------------
    # Set operations
    # ------------------------------------------------------------------
    def complement(self, bits: int) -> int:
        """NOT: every valid question position that is not set in ``bits``."""
        return self._all_mask & ~bits

    # ------------------------------------------------------------------
    # Decoding results
    # ------------------------------------------------------------------
    def positions(self, bits: int) -> list[int]:
        """Positions of the set bits, in ascending (input) order.

        Runs in time proportional to the number of matches, not the number
        of questions.
        """
        if bits < 0 or bits >> self._size:
            raise ValueError("Bitset has bits outside the valid question range.")
        found: list[int] = []
        while bits:
            lowest = bits & -bits
            found.append(lowest.bit_length() - 1)
            bits ^= lowest
        return found

    def questions_for(self, bits: int) -> list[Question]:
        """Questions for the set bits, in their original input order."""
        return [self._questions[position] for position in self.positions(bits)]
