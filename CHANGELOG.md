# Changelog

## [0.1.0] - 2026

### Features

- ✨ Parallel iterators for Python 3.14+ free-threaded mode
- 🚀 2-5.6x speedups on CPU-bound workloads
- 📦 Rich API: `map`, `filter`, `reduce`, `sum`, `count`, `min`, `max`, `any`, `all`
- 🔧 Auto-configures thread count based on CPU cores
- ✅ 40 passing tests with comprehensive coverage

### Performance

**Measured speedups** (10-core system, GIL disabled):

- Simple numeric operations: **5.6x** with 10 threads
- CPU-intensive work: **3.9x** with 8 threads
- Sweet spot: **3.7x** with 4 threads

### Implementation Highlights

- **Adaptive depth limiting**: Prevents thread pool deadlock
- **Smart work distribution**: `max_depth = max(2, min(4, log2(threads) + 1))`
- **Optimized defaults**: `min_split_size=10000`, `max_depth=8`
- **GIL-free**: Fully leverages Python 3.14's free-threaded mode

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
