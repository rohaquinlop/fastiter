# Contributing to FastIter

Thanks for your interest in contributing! This guide will help you get started.

## Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/rohaquinlop/fastiter.git
cd fastiter

# 2. Create virtual environment
python3.14t -m venv .venv
source .venv/bin/activate

# 3. Install in development mode
pip install -e ".[dev]"

# 4. Run tests
pytest tests/ -v
```

## Development Workflow

### Code Style

We use:

- **Ruff** for formatting and linting (`ruff format . && ruff check .`)
- **Ty** for type checking (`ty check`)
- **Type hints** for all public functions
- **80 character** line length (configurable in `.ruff.toml`)

Your editor can automatically sync with the project style using `.ruff.toml`.

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=fastiter tests/

# Run specific test
pytest tests/test_core.py::TestParallelRange::test_sum
```

**All tests must pass** before submitting a PR.

### Adding a New Operation

Example: Adding `take(n)` operation

**1. Create Consumer** (`consumers.py`):

```python
class TakeConsumer(Generic[T, R]):
    def __init__(self, base: Consumer[T, R], n: int):
        self.base = base
        self.n = n

    def consume_iter(self, iterator: Iterator[T]) -> R:
        limited = itertools.islice(iterator, self.n)
        return self.base.consume_iter(limited)

    def split(self) -> tuple['TakeConsumer', 'TakeConsumer']:
        # Split n between left and right
        mid = self.n // 2
        left_base, right_base = self.base.split()
        return (
            TakeConsumer(left_base, mid),
            TakeConsumer(right_base, self.n - mid)
        )

    def reduce(self, left: R, right: R) -> R:
        return self.base.reduce(left, right)
```

**2. Add Method** (`core.py`):

```python
def take(self, n: int) -> 'ParallelIterator[T]':
    """Take first n elements."""
    return TakeIterator(self, n)
```

**3. Write Tests** (`tests/test_core.py`):

```python
def test_take():
    result = par_range(0, 100).take(5).collect()
    assert sorted(result) == [0, 1, 2, 3, 4]
```

**4. Update Documentation** (`README.md`, `GUIDE.md`)

## Commit Guidelines

Use clear, descriptive messages:

```
Add take() operation

- Implement TakeConsumer
- Add tests for take()
- Update documentation

Fixes #123
```

## Pull Request Process

1. **Create a branch**: `git checkout -b feature/amazing-feature`
2. **Make changes** and commit
3. **Run tests**: `pytest tests/ -v`
4. **Run linters**: `ruff format . && ruff check . && ty check`
5. **Push**: `git push origin feature/amazing-feature`
6. **Open PR** with:
    - Clear description of changes
    - Reference to related issues
    - Test results

## What to Contribute

### Good First Issues

- Fix typos in documentation
- Add more examples
- Improve error messages
- Add tests for edge cases

### Feature Ideas

- New operations: `zip`, `enumerate`, `flatten`, `skip`, `chunks`
- NumPy array support
- Pandas DataFrame support
- Better performance profiling

### Bug Reports

Include:

- Python version and platform
- Minimal code to reproduce
- Expected vs actual behavior
- Stack trace if applicable

```python
# Bug: sum() returns wrong result
from fastiter import par_range

result = par_range(-10, 10).sum()
# Expected: 0
# Actual: -10 (wrong!)
```

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to learn and build great software together.

## Questions?

- Open an [issue](https://github.com/rohaquinlop/fastiter/issues)
- Check existing issues and PRs

## License

By contributing, you agree your contributions will be licensed under the MIT License.

---

**Thank you for contributing! 🚀**
