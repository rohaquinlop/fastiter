# Changelog

## [0.1.0] - 2026

### Features

- Parallel iterators for Python 3.14+ free-threaded mode
- API: `map`, `filter`, `reduce`, `sum`, `count`, `min`, `max`, `any`, `all`
- Auto-detects thread count based on CPU cores
- 40 tests

### Performance

Measured on a 10-core system with GIL disabled:

- Simple numeric operations: 5.6x with 10 threads
- CPU-intensive work: 3.9x with 8 threads
- 4 threads: 3.7x (balanced)

### Implementation Notes

- Adaptive depth limiting to prevent thread pool deadlock
- `max_depth = max(2, min(4, log2(threads) + 1))`
- Defaults: `min_split_size=10000`, `max_depth=8`

### Known Limitations

- Lambda overhead can dominate for simple operations
- Best suited for large datasets (500k+ items)
- Small datasets (<100k) may see overhead > benefit

### Future Roadmap

**v0.2.0**:

- Additional operations: `zip`, `enumerate`, `flatten`, `take`, `skip`
- NumPy and Pandas support
- JIT compilation for lambdas
- Better profiling tools

---

**Note**: API may change in minor versions until 1.0.0 release.
