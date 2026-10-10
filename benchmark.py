
"""Benchmark the real Question Bank Retrieval System.

Generates synthetic questions, builds the project's BitsetIndex,
and executes queries using the real parser and retrieval implementation.

Run from the project directory:
    python benchmark.py
"""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass

from qbrs.models import Difficulty, Question
from qbrs.bitset_index import BitsetIndex
from qbrs.search import run_query


@dataclass(frozen=True)
class BenchmarkResult:
    question_count: int
    query_count: int
    index_build_seconds: float
    query_total_seconds: float
    average_query_ms: float
    total_matches: int
    errors: int


def generate_questions(count: int, seed: int) -> list[Question]:
    """Generate reproducible synthetic questions."""
    rng = random.Random(seed)
    difficulties = tuple(Difficulty)
    questions = []

    for i in range(count):
        questions.append(
            Question(
                question_id=f"Q{i + 1}",
                unit=rng.randint(1, 10),
                co=f"CO{rng.randint(1, 5)}",
                bloom_level=rng.randint(1, 6),
                difficulty=rng.choice(difficulties),
            )
        )

    return questions


def generate_queries(count: int, seed: int) -> list[str]:
    """Generate queries supported by the project's parser."""
    rng = random.Random(seed)
    queries = []
    difficulties = tuple(Difficulty)

    for _ in range(count):
        unit = rng.randint(1, 10)
        co = rng.randint(1, 5)
        max_bloom = rng.randint(2, 6)
        difficulty = rng.choice(difficulties).value

        query = (
            f"FIND unit={unit} AND co=CO{co} "
            f"AND maxbloom=K{max_bloom} "
            f"AND difficulty={difficulty}"
        )
        queries.append(query)

    return queries


def run_benchmark(
    question_count: int,
    query_count: int,
    seed: int,
) -> BenchmarkResult:

    # Generate synthetic data.
    questions = generate_questions(question_count, seed)

    # Measure index construction.
    start = time.perf_counter()
    index = BitsetIndex(questions)
    index_build_seconds = time.perf_counter() - start

    # Generate reproducible queries.
    queries = generate_queries(query_count, seed + 1)

    total_matches = 0
    errors = 0

    # Measure actual query execution.
    start = time.perf_counter()

    for query in queries:
        try:
            results = run_query(index, query)
            total_matches += len(results)

        except Exception as exc:
            errors += 1

            # Avoid flooding the terminal with errors.
            if errors <= 3:
                print(f"Query error: {query!r}: {exc}")

    query_total_seconds = time.perf_counter() - start

    average_query_ms = (
        query_total_seconds / query_count * 1000
        if query_count
        else 0.0
    )

    return BenchmarkResult(
        question_count=question_count,
        query_count=query_count,
        index_build_seconds=index_build_seconds,
        query_total_seconds=query_total_seconds,
        average_query_ms=average_query_ms,
        total_matches=total_matches,
        errors=errors,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark the Question Bank Retrieval System."
    )

    parser.add_argument(
        "--questions",
        type=int,
        default=100_000,
        help="Number of synthetic questions (default: 100000)",
    )

    parser.add_argument(
        "--queries",
        type=int,
        default=10_000,
        help="Number of queries (default: 10000)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20261010,
        help="Random seed for reproducible results",
    )

    args = parser.parse_args()

    if args.questions < 1 or args.queries < 1:
        parser.error(
            "--questions and --queries must be positive integers"
        )

    print("Question Bank Retrieval System Benchmark")
    print("-" * 45)
    print(f"Questions:             {args.questions:,}")
    print(f"Queries:               {args.queries:,}")
    print(f"Random seed:           {args.seed}")

    result = run_benchmark(
        args.questions,
        args.queries,
        args.seed,
    )

    print("\nBenchmark Results")
    print("-" * 45)
    print(
        f"Index construction:    "
        f"{result.index_build_seconds:.6f} seconds"
    )
    print(
        f"Total query time:      "
        f"{result.query_total_seconds:.6f} seconds"
    )
    print(
        f"Average query time:    "
        f"{result.average_query_ms:.4f} ms/query"
    )
    print(f"Total matched rows:    {result.total_matches:,}")
    print(f"Query errors:          {result.errors}")

    if result.errors:
        print("\nSTATUS: FAILED")
        return 1

    print("\nSTATUS: COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
