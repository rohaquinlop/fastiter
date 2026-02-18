# FastIter

Parallel iterators for Python 3.14+, built on the free-threaded mode (no GIL).

```python
from fastiter import par_range

result = par_range(0, 3_000_000).map(lambda x: x * x).sum()
```

## Features

- Parallel processing for CPU-bound work on large datasets
- Familiar iterator API (`map`, `filter`, `reduce`, `sum`, etc.)
- Requires Python 3.14 free-threaded build (`python3.14t`)
- 40 tests

## Installation

```bash
pip install fastiter
uv add fastiter
```

**Requirements**: Python 3.14+ **free-threaded build required** (`python3.14t`)

> ⚠️ **With GIL enabled, FastIter will be slower than sequential code** for CPU-bound work - threads contend on the GIL and add overhead with no benefit. Free-threaded mode is not optional for real speedups.

## Quick Start

```python
from fastiter import par_range, into_par_iter, set_num_threads

# Configure threads (optional, auto-detects CPU count)
set_num_threads(4)

# Process ranges in parallel
total = par_range(0, 1_000_000).sum()

# Chain operations
evens = (
    par_range(0, 10_000)
    .filter(lambda x: x % 2 == 0)
    .map(lambda x: x ** 2)
    .collect()
)

# Work with lists
data = list(range(100_000))
result = into_par_iter(data).map(lambda x: x * 2).sum()
```

## Performance

**Measured on 10-core system with Python 3.14t (GIL disabled)**:

| Threads | Simple Sum (3M items) | CPU-Intensive Work |
| ------- | --------------------- | ------------------ |
| 2       | 1.9x                  | 1.9x               |
| 4       | 3.7x                  | 2.3x               |
| 8       | 4.2x                  | 3.9x               |
| 10      | **5.6x**              | 3.7x               |

**Sweet spot**: 4 threads for balanced performance

### When to use FastIter

✅ **Works great**:

- Large datasets (500k+ items)
- CPU-bound computations
- Simple numeric operations
- Pure functions without shared state

❌ **Not recommended**:

- Small datasets (<100k items) - overhead dominates
- I/O-bound operations - use `asyncio` instead
- Heavy lambda usage - Python function call overhead

## API

### Create parallel iterators

```python
par_range(start, stop, step=1)    # Parallel range
into_par_iter(iterable)            # Convert any iterable
```

### Operations

```python
.map(func)              # Transform each element
.filter(predicate)      # Keep matching elements
.sum()                  # Sum all elements
.count()                # Count elements
.min() / .max()         # Find min/max
.any() / .all()         # Test predicates
.reduce(id, op)         # Custom reduction
.collect()              # Gather to list
.for_each(func)         # Execute function on each
```

### Configuration

```python
from fastiter import set_num_threads

set_num_threads(4)      # Set thread count
# Or: export FASTITER_NUM_THREADS=4
```

## Examples

**CPU-intensive work**:

```python
def expensive_computation(x):
    result = x
    for _ in range(20):
        result = (result * 1.1 + 1) % 1000000
    return int(result)

# 3.9x faster with 8 threads
result = par_range(0, 200_000).map(expensive_computation).sum()
```

**Simple aggregations**:

```python
# Sum of squares
total = par_range(0, 1_000_000).map(lambda x: x * x).sum()

# Count evens
count = par_range(0, 1_000_000).filter(lambda x: x % 2 == 0).count()

# Find maximum
maximum = into_par_iter([1, 5, 3, 9, 2]).max()
```

**Complex pipelines**:

```python
result = (
    par_range(0, 1_000_000)
    .filter(lambda x: x % 2 == 0)
    .map(lambda x: x * x)
    .filter(lambda x: x > 1000)
    .sum()
)
```

## How It Works

FastIter uses a divide-and-conquer approach:

1. **Split**: Data is recursively divided into chunks
2. **Distribute**: Chunks are processed across threads
3. **Reduce**: Results are combined back together

**Adaptive depth limiting** is used to prevent thread pool exhaustion.

## Benchmarks

Run your own benchmarks (must use free-threaded build):

```bash
# Full benchmark suite
uv run --python 3.14t python benchmarks/benchmark.py

# Quick demo
uv run --python 3.14t python main.py

# Run tests
uv run --python 3.14t pytest tests/ -v
```

> Running benchmarks with `python3.14` (GIL enabled) will show worse-than-sequential numbers - that's expected and correct behavior, not a bug.

## Architecture

```
fastiter/
├── protocols.py    # Producer/Consumer abstractions
├── core.py         # ParallelIterator with 15+ operations
├── bridge.py       # Work distribution (adaptive depth limiting)
├── consumers.py    # Map, Filter, Reduce, etc.
└── producers.py    # Range, List, Tuple data sources
```

See [GUIDE.md](GUIDE.md) for implementation details.

## Requirements

**Python 3.14+ free-threaded build (`python3.14t`) is required for speedups.**

FastIter uses `ThreadPoolExecutor` under the hood. With the GIL enabled, Python threads cannot run CPU-bound bytecode simultaneously - they serialize and add overhead, making parallel execution **slower** than sequential for the workloads FastIter targets. Free-threading is not a recommendation; it is what makes the library work.

```bash
# Install the free-threaded build
uv python install 3.14t   # or pyenv install 3.14t

# Verify GIL is disabled
python3.14t -c "import sys; print('GIL disabled:', not sys._is_gil_enabled())"
# Should print: GIL disabled: True

# If you import FastIter with the GIL enabled, you will see a RuntimeWarning
```

**What happens without free-threading?**

| Mode                    | Result                                                       |
| ----------------------- | ------------------------------------------------------------ |
| `python3.14t` (GIL off) | ✅ 2–5.6x speedup                                            |
| `python3.14` (GIL on)   | ❌ Slower than sequential (thread overhead + GIL contention) |
| Python < 3.14           | ❌ Not supported                                             |

## FAQ

**Why threads instead of `multiprocessing.Pool`?**

Processes require pickling every argument and result across a process boundary ([Python docs: Exchanging objects between processes](https://docs.python.org/3/library/multiprocessing.html#exchanging-objects-between-processes)). For fine-grained numeric operations on large datasets, that serialisation cost dominates — you spend more time copying data than computing it. Threads share memory directly, so the only overhead is task submission and result collection. With the GIL gone, threads get true parallel CPU execution with none of the process spawn (~50–100ms per worker) or pickle cost.

|                    | `multiprocessing.Pool`                                                                               | FastIter (threads)                      |
| ------------------ | ---------------------------------------------------------------------------------------------------- | --------------------------------------- |
| Spawn cost         | ~50–100ms per worker                                                                                 | ~0.1ms per thread                       |
| Data serialisation | Pickle on every call ([docs](https://docs.python.org/3/library/pickle.html#comparison-with-marshal)) | None (shared memory)                    |
| Memory per worker  | Full process copy                                                                                    | Shared                                  |
| Sweet spot         | Few coarse, long-running tasks                                                                       | Many fine-grained ops on large datasets |

You can measure this directly with the included benchmark:

```bash
uv run --python 3.14t python benchmarks/benchmark_vs_multiprocessing.py
```

If you have a handful of coarse, long-running tasks (seconds each, not microseconds), `multiprocessing.Pool` is still the right tool.

**Isn't free-threaded Python still experimental?**

"Experimental" describes the ecosystem catch-up, not the feature itself. The free-threaded build (`3.14t`) is a fully supported CPython release variant - it ships with the same test suite, same stability guarantees, and `sys._is_gil_enabled()` is stable API. The risk is with C extensions that aren't thread-safe yet; FastIter has no C extension dependencies, so that risk doesn't apply here.

PEP 703 is accepted and the GIL becomes more optional each release.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- Code style guidelines
- How to add new operations
- Testing requirements

## License

MIT License - see [LICENSE](LICENSE)

## Inspiration

- [Rayon](https://github.com/rayon-rs/rayon) - Rust's data parallelism library
- [PEP 703](https://peps.python.org/pep-0703/) - Making the GIL optional
- [Tutorial](https://geo-ant.github.io/blog/2022/implementing-parallel-iterators-rayon/) - Implementing parallel iterators

## Version

**v0.1.0** - Experimental / locally tested

- 40 passing tests
- 2-5.6x measured speedups
- Complete documentation

---

[GitHub](https://github.com/rohaquinlop/fastiter) • [Issues](https://github.com/rohaquinlop/fastiter/issues)
