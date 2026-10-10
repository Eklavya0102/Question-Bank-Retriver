# Question Bank Retrieval System

## 1. Project Overview

The Question Bank Retrieval System is a Python-based application designed to retrieve examination questions efficiently using metadata-based filtering and Boolean queries.

Each question contains the following attributes:

- **Question ID:** Unique identifier for the question.
- **Unit:** Unit to which the question belongs.
- **CO (Course Outcome):** Learning outcome associated with the question.
- **Bloom Level:** Cognitive level, ranging from K1 to K6.
- **Difficulty:** EASY, MEDIUM, or HARD.

The system uses bitset indexing and query parsing to retrieve questions that match specified conditions. It is designed to support efficient retrieval from large question banks.

## 2. Objectives

- Retrieve questions using Unit, CO, Bloom level, and Difficulty.
- Support Boolean operators such as AND, OR, and NOT.
- Support grouped expressions using parentheses.
- Use bitset indexing to perform efficient query operations.
- Support maximum Bloom-level filtering.
- Evaluate retrieval performance on large datasets.

## 3. Technologies Used

- Python 3
- Python standard library
- Bitwise operations for bitset-based retrieval
- Recursive descent parsing or the query parser implemented in the project
- Python timing utilities for performance benchmarking

No external dependencies are required unless specified by the project's existing configuration.

## 4. Project Structure

The project is organized into modules similar to the following:

```text
question_bank_retrieval/
├── main.py
├── benchmark.py
├── README.md
└── qbrs/
    ├── __init__.py
    ├── models.py
    ├── bitset_index.py
    ├── query_parser.py
    └── search.py
```

**File descriptions:**

- `main.py`: Main entry point for running the application.
- `benchmark.py`: Generates synthetic questions and measures retrieval performance.
- `models.py`: Defines the question data model and related attributes.
- `bitset_index.py`: Builds indexes used for efficient question retrieval.
- `query_parser.py`: Parses supported query expressions.
- `search.py`: Evaluates queries and retrieves matching questions.
- `README.md`: Project documentation.

The exact filenames should match the files present in your project.

## 5. Input Format

The application accepts input manually through the terminal.

The first line contains the number of questions, `n`.

The next `n` lines contain one question per line in the following format:

```text
QuestionID Unit CO BloomLevel Difficulty
```

The line after the question records contains the search query.

### Example Input

```text
4
P1 1 CO1 K2 EASY
P2 1 CO1 K4 HARD
P3 2 CO2 K3 MEDIUM
P4 1 CO1 K3 MEDIUM
FIND unit=1 co=CO1 maxbloom=K3
```

### Expected Output

```text
P1 P4
```

### Explanation

- P1 matches Unit 1, CO1, and the maximum Bloom level K3.
- P2 is excluded because its Bloom level is K4.
- P3 is excluded because it belongs to Unit 2 and CO2.
- P4 matches all the specified conditions.

The matching question IDs are returned in their original input order.

## 6. Query Language

The query language allows users to retrieve questions using metadata conditions.

### Basic Query

```text
FIND unit=1 co=CO1 maxbloom=K3
```

This retrieves questions belonging to Unit 1 and CO1 whose Bloom level does not exceed K3.

### Boolean Operators

**AND**

Both conditions must be satisfied.

```text
FIND unit=1 AND co=CO1
```

**OR**

At least one condition must be satisfied.

```text
FIND unit=1 OR unit=2
```

**NOT**

Excludes questions matching a condition.

```text
FIND NOT difficulty=HARD
```

**Parentheses**

Parentheses group expressions together.

```text
FIND unit=1 AND (co=CO1 OR co=CO2)
```

### Operator Precedence

The intended precedence is:

1. Parentheses
2. NOT
3. AND
4. OR

The implementation's parser determines the exact accepted syntax.

## 7. Bloom-Level Filtering

Bloom levels represent increasing levels of cognitive complexity, from K1 to K6.

A query using:

```text
maxbloom=K3
```

allows questions at levels K1, K2, and K3.

It excludes questions at K4, K5, and K6.

This is a maximum-level condition rather than an exact Bloom-level match.

## 8. Bitset Indexing

The system uses bitsets to represent sets of questions.

Each bit position corresponds to a question in the dataset. A bit value of 1 indicates that the question matches a particular indexed attribute; 0 indicates that it does not.

For example, an index for Unit 1 identifies all questions belonging to Unit 1.

Bitwise operations combine these indexes:

- **AND (`&`):** Finds questions common to both sets.
- **OR (`|`):** Finds questions belonging to either set.
- **NOT:** Identifies questions outside a set, restricted to valid question positions.

For a maximum Bloom level of K3, the system combines the indexes for K1, K2, and K3.

Bitset operations help reduce the amount of repeated work required to evaluate queries against large question banks.

## 9. Running the Application

### Prerequisites

Install Python 3 on your computer.

Verify the installation:

```bash
python --version
```

On systems where Python is available as `python3`, use:

```bash
python3 --version
```

### Start the Application

Open a terminal in the project directory and execute:

```bash
python main.py
```

Enter the number of questions, the question records, and the query in the specified format.

Use `python3 main.py` if required by your environment.

## 10. Performance Benchmarking

The project includes a benchmark script to evaluate the retrieval system on a large synthetic dataset.

The benchmark is intended to measure:

- Index construction time.
- Total query execution time.
- Average query execution time.
- Number of questions processed.
- Number of queries executed.
- Number of matching results.
- Query errors, if any.

### Run a Smaller Benchmark

```bash
python benchmark.py --questions 10000 --queries 1000
```

### Run the Full Benchmark

```bash
python benchmark.py
```

By default, the benchmark is configured for:

- **100,000 questions**
- **10,000 queries**

The benchmark uses a fixed random seed to make the generated workload reproducible.

### Performance Measurements

The benchmark reports the actual timings measured during execution.

Results depend on the computer, Python version, dataset, query complexity, and implementation.

Do not treat example timings as guaranteed performance results.

## 11. Benchmark Methodology

The benchmark generates synthetic questions with varying Units, Course Outcomes, Bloom levels, and Difficulty values.

It then builds the application's bitset index and executes a collection of generated queries using the project's retrieval implementation.

The benchmark measures index construction separately from query execution.

Average query time is calculated as:

```text
Average query time = Total query execution time / Number of queries
```

The benchmark is designed to assess performance at the required dataset and query scale. It does not replace correctness tests for every supported query expression.

## 12. Error Handling and Limitations

The application should validate question records and reject malformed or unsupported queries with clear error messages.

Potential limitations include:

- Invalid metadata values.
- Malformed Boolean expressions.
- Unmatched parentheses.
- Empty result sets.
- Performance variations across environments.

The exact validation rules depend on the implemented modules.

Ranked retrieval by a requested difficulty distribution is a separate feature from ordinary Boolean filtering. It should be documented as supported only if that functionality has been implemented.

## 13. Future Improvements

Possible extensions