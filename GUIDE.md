# FastIter Complete Guide

## Table of Contents

- [Getting Started](#getting-started)
- [Performance Guide](#performance-guide)
- [Architecture](#architecture)
- [Advanced Usage](#advanced-usage)

---

## Getting Started

### Installation

```bash
pip install fastiter

# Or from source
git clone https://github.com/rohaquinlop/fastiter.git
cd fastiter
pip install -e .
```

### Your First Parallel Iterator

```python
from fastiter import par_range

# Sum numbers from 0 to 999,999 in parallel
result = par_range(0, 1_000_000).sum()
print(f"Sum: {result}")
```

### Common Patterns

**Transform elements**:

```python
squares = par_range(0, 10).map(lambda x: x ** 2).collect()
# [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

**Filter elements**:

```python
evens = par_range(0, 20).filter(lambda x: x % 2 == 0).collect()
# [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
```

**Custom reduction**:

```python
factorial = par_range(1, 11).reduce(
    lambda: 1,              # Identity value
    lambda a, b: a * b      # Reduction operation
)
# 10! = 3,628,800
```

**Chain operations**:

```python
result = (
    par_range(0, 1000)
    .filter(lambda x: x % 2 == 0)
    .map(lambda x: x ** 2)
    .sum()
)
```

### Working with Lists

```python
from fastiter import into_par_iter

# Process a list
data = [1, 2, 3, 4, 5]
result = into_par_iter(data).map(lambda x: x * 2).collect()

# Process strings
words = ["hello", "world", "parallel"]
lengths = into_par_iter(words).map(len).collect()
```

### Configuration

```python
from fastiter import set_num_threads

# Use 4 threads (recommended sweet spot)
set_num_threads(4)

# Or use all cores
import os
set_num_threads(os.cpu_count())

# Or via environment variable
# export FASTITER_NUM_THREADS=4
```

---

## Performance Guide

### Benchmark Results

**10-core system, Python 3.14t, GIL disabled, module-level worker functions**:

```
Sum of Squares (10M items, map(square).sum()):
  2 threads:  ~1.4x speedup
  4 threads:  ~2.0x speedup
  8 threads:  ~3.3x speedup
  16 threads: ~5.1x speedup

Min / Max over range (10M items):
  10 threads: ~5.5x speedup

CPU-Intensive (200k items, 20 float ops per element):
  10 threads: ~4x speedup
```

> **Important**: these numbers require worker functions defined at **module level**.
> Closure functions (lambdas or nested `def` inside another function) cause cell
> contention in free-threaded CPython and can make parallel code 10–30x _slower_
> than sequential. See [Closure Cell Contention](#closure-cell-contention-in-free-threaded-python) below.

### Performance Guidelines

**✓ Use FastIter when**:

- Dataset has 500k+ items
- Operations are CPU-bound
- Work per element is non-trivial
- Functions are pure (no shared state)

**✗ Don't use FastIter when**:

- Dataset has <100k items (overhead > benefit)
- Operations are I/O-bound (use asyncio)
- Heavy use of lambdas (function call overhead)

### Optimal Thread Counts

| Dataset Size | Recommended Threads | Expected Speedup |
| ------------ | ------------------- | ---------------- |
| < 100k       | 1 (sequential)      | 1.0x             |
| 100k - 500k  | 2-4                 | 1.5x - 2.5x      |
| 500k - 2M    | 4-6                 | 2.5x - 4.0x      |
| > 2M         | 6-10                | 3.5x - 5.6x      |

### Benchmarking Tips

```python
import time
from fastiter import par_range

N = 1_000_000

# Parallel
start = time.perf_counter()
p_result = par_range(0, N).map(lambda x: x * x).sum()
p_time = time.perf_counter() - start

# Sequential
start = time.perf_counter()
s_result = sum(x * x for x in range(N))
s_time = time.perf_counter() - start

print(f"Speedup: {s_time / p_time:.2f}x")
```

### Closure Cell Contention in Free-Threaded Python

This is the most important performance pitfall specific to Python 3.14t.

In free-threaded CPython, every function defined **inside another function** (a closure) carries a reference to its enclosing frame's cell objects. When multiple threads call the same closure simultaneously, they all contend on a per-cell lock — serialising execution and eliminating any parallelism gain.

**Slow** — closure defined inside a function, all threads contend on cell lock:

```python
def run():
    fn = lambda x: x * x          # closes over run()'s frame
    par_range(0, 5_000_000).map(fn).sum()   # ~33x slower than sequential
```

**Fast** — function defined at module level, no cell state to contend on:

```python
def square(x):                     # module-level: no closure cells
    return x * x

par_range(0, 5_000_000).map(square).sum()   # ~3x faster than sequential
```

The same applies to lambdas passed inline when the call site is itself inside a function:

```python
# Also slow — the lambda closes over the enclosing function's frame
def benchmark():
    return par_range(0, 5_000_000).map(lambda x: x * x).sum()
```

**Rule of thumb**: any callable you pass to `map()`, `filter()`, `reduce()`, `any()`, or `all()` should be defined at module level (or as a method of a class) to avoid cell contention.

FastIter's own built-in operations (`sum`, `min`, `max`, `count`) use module-level C-callable helpers internally and are not affected by this issue.

### When Lambda Overhead Matters

**Slow** (closure lambda — cell contention serialises threads):

```python
def run():
    # Lambda closes over run()'s frame — all threads serialise
    par_range(0, 5_000_000).map(lambda x: x * x).sum()
```

**Fast** (module-level function — no contention):

```python
def square(x):
    return x * x

# 3-4x FASTER with 10 threads
par_range(0, 5_000_000).map(square).sum()
```

**Fast** (CPU-intensive work with module-level function):

```python
def expensive(x):
    result = x
    for _ in range(20):
        result = (result * 1.1 + 1) % 1000000
    return int(result)

# 4-5x FASTER with 10 threads
par_range(0, 200_000).map(expensive).sum()
```

---

## Architecture

### Core Concepts

FastIter uses a **Producer-Consumer** pattern inspired by Rust's Rayon:

**Producer**: Splittable data source

```python
class Producer:
    def split_at(index) -> (left, right)
    def into_iter() -> Iterator
```

**Consumer**: Processes elements and combines results

```python
class Consumer:
    def consume_iter(iterator) -> Result
    def split() -> (left_consumer, right_consumer)
    def reduce(left, right) -> Result
```

### Execution Flow

```
1. Create Producer (e.g., RangeProducer[0..8])
2. Split recursively
   [0..8] → [0..4], [4..8]
   [0..4] → [0..2], [2..4]
   [4..8] → [4..6], [6..8]
3. Process in threads
   Thread 1: sum([0,1,2,3]) = 6
   Thread 2: sum([4,5,6,7]) = 22
4. Reduce results
   6 + 22 = 28
```

### Key Components

**Protocols** (`protocols.py`):

- `Producer[T]` - Splittable data sources
- `Consumer[T, R]` - Element processors
- `UnindexedProducer[T]` - For unknown-length streams

**Core** (`core.py`):

- `ParallelIterator` - Base class with operations
- `IndexedParallelIterator` - With known length

**Bridge** (`bridge.py`):

- Adaptive depth limiting prevents deadlock
- Formula: `max_depth = max(2, min(4, log2(threads) + 1))`
- Only top levels parallelize, deeper levels go sequential

**Consumers** (`consumers.py`):

- MapConsumer, FilterConsumer, ReduceConsumer
- SumConsumer, CountConsumer, etc.

**Producers** (`producers.py`):

- RangeProducer, ListProducer, TupleProducer

### Why Adaptive Depth Limiting?

**Problem**: Recursive task submission can exhaust thread pool
**Solution**: Only parallelize top ~4 levels, rest sequential

```python
# With 8 threads: max_parallel_depth = 4
# Creates up to 16 parallel tasks (2^4)
# Thread pool can handle without deadlock
```

---

## Advanced Usage

### Custom Reductions

```python
# Product
product = par_range(1, 11).reduce(
    lambda: 1,
    lambda a, b: a * b
)

# Concatenate strings
result = into_par_iter(["a", "b", "c"]).reduce(
    lambda: "",
    lambda a, b: a + b
)
```

### Find Operations

```python
# Find min with key function
words = ["a", "abc", "ab", "abcdef"]
longest = into_par_iter(words).max(key=len)
shortest = into_par_iter(words).min(key=len)
```

### Predicates

```python
# Check if any element matches
has_even = par_range(0, 100).any(lambda x: x % 2 == 0)

# Check if all elements match
all_positive = par_range(1, 100).all(lambda x: x > 0)
```

### Configuration Tuning

```python
from fastiter.config import ThreadPoolConfig

config = ThreadPoolConfig.global_config()

# Larger = less parallelism, less overhead
config.min_split_size = 50000

# Smaller = more parallelism (may cause overhead)
config.min_split_size = 5000

# Default: 10000 (balanced)
```

### Adding New Operations

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add custom operations.

---

## Troubleshooting

**Q: Why is parallel slower than sequential?**

A: Common causes, in order of likelihood:

1. **Closure cell contention** — worker function is defined inside another function (lambda or nested `def`). In free-threaded CPython, all threads serialise on the closure's cell lock. Move the function to module level. This is the most common cause of unexpected slowdowns.
2. **Dataset too small** — fewer than ~100k items; thread overhead dominates.
3. **GIL still enabled** — not using the free-threaded build. Check with `sys._is_gil_enabled()`.
4. **I/O-bound work** — threads don't help; use `asyncio` instead.

**Q: How to verify GIL is disabled?**

```python
import sys
print("GIL disabled:", not sys._is_gil_enabled())
```

**Q: What thread count should I use?**

- Start with 4 threads (recommended sweet spot)
- Scale up for larger datasets
- Measure with your actual workload

**Q: Can I use FastIter with NumPy?**

Not yet - FastIter works with Python iterables. NumPy arrays should use NumPy's own parallelism for now.

---

## FAQ

### Why not just use `multiprocessing.Pool`?

Processes and threads have different trade-offs:

|                    | `multiprocessing.Pool`     | FastIter (threads)            |
| ------------------ | -------------------------- | ----------------------------- |
| Parallelism today  | ✅ Any Python              | ✅ Python 3.14t only          |
| Spawn cost         | ~50–100ms per worker       | ~0.1ms per thread             |
| Memory per worker  | Full process copy          | Shared memory                 |
| Data serialisation | Pickle (every call)        | None                          |
| Shared state       | Requires `Manager` / pipes | Direct access                 |
| Sweet spot         | Long-running, coarse tasks | Short-to-medium, fine-grained |

Processes are a good fit for a handful of long-running tasks. FastIter is better suited for many small operations on large datasets, where pickling overhead would dominate.

---

### Is free-threaded Python stable enough to use?

The free-threaded build (`3.14t`) is a supported CPython variant — not experimental in the sense of unstable. The main caveats are:

- Some C extensions may not be thread-safe yet. FastIter has no C extension dependencies, so this doesn't apply.
- Single-threaded performance may be ~5–10% slower due to reference counting changes.
- The ecosystem is still catching up, but pure Python code works fine.

If you can't run `python3.14t`, use `multiprocessing.Pool` instead. FastIter requires the free-threaded build to be useful.

```python
import sys
if sys._is_gil_enabled():
    raise RuntimeError("FastIter requires a free-threaded Python build (python3.14t)")
```

---

## Running Examples

```bash
# Basic usage examples
uv run --python 3.14t python examples/basic_usage.py

# Performance benchmarks (FastIter vs sequential)
uv run --python 3.14t python benchmarks/benchmark.py

# FastIter vs multiprocessing.Pool
uv run --python 3.14t python benchmarks/benchmark_vs_multiprocessing.py

# Interactive demo
uv run --python 3.14t python main.py

# Run tests
uv run --python 3.14t pytest tests/ -v
```

---

## Resources

- [Rayon Documentation](https://docs.rs/rayon/) - Original Rust inspiration
- [PEP 703](https://peps.python.org/pep-0703/) - Free-threaded Python proposal
- [Tutorial](https://geo-ant.github.io/blog/2022/implementing-parallel-iterators-rayon/) - Implementing parallel iterators

---

**Questions?** [Open an issue](https://github.com/rohaquinlop/fastiter/issues) or start a [discussion](https://github.com/rohaquinlop/fastiter/discussions)
