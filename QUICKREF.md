# FastIter Quick Reference

## Installation
```bash
pip install fastiter
```

## Basic Usage
```python
from fastiter import par_range, into_par_iter, set_num_threads

# Configure (optional)
set_num_threads(4)

# Create parallel iterators
par_range(0, 1000)          # Range
into_par_iter([1, 2, 3])    # From list
```

## Operations

### Transform
```python
.map(lambda x: x * 2)       # Apply function
.filter(lambda x: x > 0)    # Keep matching elements
```

### Aggregate
```python
.sum()                      # Sum elements
.count()                    # Count elements
.min() / .max()             # Find min/max
```

### Reduce
```python
.reduce(
    lambda: 0,              # Identity
    lambda a, b: a + b      # Combine operation
)
```

### Collect
```python
.collect()                  # Gather to list
.any(predicate)             # Test any
.all(predicate)             # Test all
.for_each(func)             # Execute on each
```

## Examples

```python
# Sum of squares
par_range(0, 1000000).map(lambda x: x * x).sum()

# Count evens
par_range(0, 1000).filter(lambda x: x % 2 == 0).count()

# Custom reduction
par_range(1, 11).reduce(lambda: 1, lambda a, b: a * b)  # 10!

# Complex pipeline
(par_range(0, 10000)
    .filter(lambda x: x % 2 == 0)
    .map(lambda x: x ** 2)
    .sum())
```

## Performance Tips

✅ **Use when**:
- 500k+ items
- CPU-bound work
- 4-8 threads

❌ **Avoid when**:
- <100k items
- I/O-bound
- Simple lambdas

## Docs
- Full guide: [GUIDE.md](GUIDE.md)
- Main docs: [README.md](README.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
