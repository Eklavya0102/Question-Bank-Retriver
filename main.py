"""Entry point: reads questions and a query from stdin, prints matching IDs."""

from __future__ import annotations

import sys

from qbrs.bitset_index import BitsetIndex
from qbrs.errors import InputError
from qbrs.filtering import format_result
from qbrs.input_handler import read_dataset
from qbrs.query_parser import parse_query
from qbrs.search import evaluate


def main() -> int:
    try:
        questions, query_text, query_line_no = read_dataset(sys.stdin)
        query = parse_query(query_text, query_line_no)
        index = BitsetIndex(questions)
        matches = index.questions_for(evaluate(query, index))
    except InputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(format_result(matches))
    return 0


if __name__ == "__main__":
    sys.exit(main())
