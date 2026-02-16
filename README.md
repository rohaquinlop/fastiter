# FastIter 🚀

> Parallel iterators for Python 3.14+ that actually work

**2-5x faster** processing for large datasets using Python's new free-threaded mode.

```python
from fastiter import par_range

# Process 3 million items in parallel - 5.6x faster!
result = par_range(0, 3_000_000).map(lambda x: x * x).sum()
```

## Why FastIter?

- ✅ **Real speedups**: 2-5.6x faster on CPU-bound work
- ✅ **Drop-in replacement**: Familiar iterator API
- ✅ **No GIL**: Takes advantage of Python 3.14's free-threaded mode
- ✅ **Production ready**: 40 tests, comprehensive docs

## Installation

```bash
pip install fastiter
uv add fastiter
```

**Requirements**: Python 3.14+ (free-threaded build recommended)

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
| 2       | 1.9x (96% eff)        | 1.9x (95% eff)     |
| 4       | 3.7x (92% eff)        | 2.3x (58% eff)     |
| 8       | 4.2x (52% eff)        | 3.9x (49% eff)     |
| 10      | **5.6x** (56% eff)    | 3.7x (37% eff)     |

**Sweet spot**: 4 threads for best efficiency (90%+)

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

**CPU-intensive work** (where FastIter shines):

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

FastIter uses a divide-and-conquer approach inspired by Rust's Rayon:

1. **Split**: Data is recursively divided into chunks
2. **Distribute**: Chunks are processed across threads
3. **Reduce**: Results are combined back together

Key innovation: **Adaptive depth limiting** prevents thread pool exhaustion while maximizing parallelism.

## Benchmarks

Run your own benchmarks:

```bash
# Full benchmark suite
uv run --python 3.14t python benchmarks/benchmark.py

# Quick demo
uv run --python 3.14t python main.py

# Run tests
uv run --python 3.14t pytest tests/ -v
```

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

**Python 3.14+** with free-threaded mode for best performance:

```bash
# Check if you have the right Python
python3.14t --version
# Should show: Python 3.14.x free-threading build

# Verify GIL is disabled
python3.14t -c "import sys; print('GIL disabled:', not sys._is_gil_enabled())"
```

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

**v0.1.0** - Production ready

- 40 passing tests
- 2-5.6x measured speedups
- Complete documentation

---

**Made with ❤️ for high-performance Python**

[GitHub](https://github.com/yourusername/fastiter) • [Issues](https://github.com/yourusername/fastiter/issues)
