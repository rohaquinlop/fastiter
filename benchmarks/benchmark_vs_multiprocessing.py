"""
Benchmark: FastIter (threads) vs multiprocessing.Pool vs sequential Python.

This benchmark validates the claim in the README that pickling overhead makes
multiprocessing.Pool slower than thread-based parallelism for fine-grained
numeric operations on large datasets.

Run with the free-threaded build for FastIter results:
    uv run --python 3.14t python benchmarks/benchmark_vs_multiprocessing.py

You can also run with a regular build to see the GIL-enabled baseline:
    python benchmarks/benchmark_vs_multiprocessing.py

Background on pickling overhead:
    https://docs.python.org/3/library/multiprocessing.html#exchanging-objects-between-processes
    https://docs.python.org/3/library/pickle.html#comparison-with-marshal
"""

import multiprocessing
import multiprocessing.pool
import os
import time
from collections.abc import Callable
from typing import Any

# FastIter is only useful under the free-threaded build, but the benchmark
# still imports it so the comparison is always apples-to-apples.
try:
    from fastiter import par_range, set_num_threads

    FASTITER_AVAILABLE = True
except ImportError:
    FASTITER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Worker functions at module level (required for pickling with multiprocessing)
# ---------------------------------------------------------------------------


def _square(x: int) -> int:
    return x * x


def _is_even(x: int) -> bool:
    return x % 2 == 0


def _expensive(x: int) -> int:
    """Simulate CPU-bound work: ~20 iterations of float arithmetic."""
    result = float(x)
    for _ in range(20):
        result = (result * 1.1 + 1) % 1_000_000
    return int(result)


def _square_if_even(x: int) -> int | None:
    """Return x² if x is even, else None (used for filter+map pipelines)."""
    if x % 2 == 0:
        return x * x
    return None


# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------


def _measure(fn: Callable[[], Any], iterations: int = 3) -> tuple[float, Any]:
    """Return (average_seconds, last_result)."""
    # warm-up
    result = fn()
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - t0)
    return sum(times) / len(times), result


def _row(label: str, t: float, baseline: float) -> str:
    speedup = baseline / t if t > 0 else float("inf")
    return f"  {label:<32s} {t:.4f}s   {speedup:>6.2f}x"


def _header(title: str, n: int) -> None:
    print(f"\n{'=' * 64}")
    print(f"  {title}  (N={n:,})")
    print(f"{'=' * 64}")
    print(f"  {'Method':<32s} {'Time':>8s}   {'Speedup vs seq':>14s}")
    print(f"  {'-' * 60}")


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------


def bench_sum_of_squares(
    pool: multiprocessing.pool.Pool, n: int = 5_000_000
) -> None:
    """Sum of x² for x in range(n)."""
    _header("Sum of Squares  [map → sum]", n)

    # sequential baseline
    seq_time, _ = _measure(lambda: sum(x * x for x in range(n)))
    print(_row("sequential (generator)", seq_time, seq_time))

    # multiprocessing.Pool.map  — chunks the range into equal pieces
    chunk = max(1, n // (multiprocessing.cpu_count() * 4))
    mp_time, _ = _measure(
        lambda: sum(pool.map(_square, range(n), chunksize=chunk))
    )
    print(_row("multiprocessing.Pool.map", mp_time, seq_time))

    # multiprocessing.Pool.imap_unordered — lower overhead variant
    imap_time, _ = _measure(
        lambda: sum(pool.imap_unordered(_square, range(n), chunksize=chunk))
    )
    print(_row("multiprocessing.Pool.imap_unordered", imap_time, seq_time))

    if FASTITER_AVAILABLE:
        fi_time, _ = _measure(lambda: par_range(0, n).map(_square).sum())
        print(_row("FastIter (threads)", fi_time, seq_time))


def bench_filter_sum(
    pool: multiprocessing.pool.Pool, n: int = 5_000_000
) -> None:
    """Sum of even numbers in range(n)."""
    _header("Filter Even Numbers → Sum", n)

    seq_time, _ = _measure(lambda: sum(x for x in range(n) if x % 2 == 0))
    print(_row("sequential (generator)", seq_time, seq_time))

    chunk = max(1, n // (multiprocessing.cpu_count() * 4))

    # multiprocessing: map + filter in one pass via _square_if_even
    mp_time, _ = _measure(
        lambda: sum(
            v
            for v in pool.map(_square_if_even, range(n), chunksize=chunk)
            if v is not None
        )
    )
    print(_row("multiprocessing.Pool.map (filter+sum)", mp_time, seq_time))

    if FASTITER_AVAILABLE:
        fi_time, _ = _measure(lambda: par_range(0, n).filter(_is_even).sum())
        print(_row("FastIter (threads)", fi_time, seq_time))


def bench_cpu_intensive(
    pool: multiprocessing.pool.Pool, n: int = 200_000
) -> None:
    """CPU-intensive per-element work — the sweet spot for multiprocessing."""
    _header("CPU-Intensive Work  [expensive fn → sum]", n)
    print("  (This is where multiprocessing.Pool is expected to compete best)")

    seq_time, _ = _measure(lambda: sum(_expensive(x) for x in range(n)))
    print(_row("sequential", seq_time, seq_time))

    chunk = max(1, n // (multiprocessing.cpu_count() * 4))
    mp_time, _ = _measure(
        lambda: sum(pool.map(_expensive, range(n), chunksize=chunk))
    )
    print(_row("multiprocessing.Pool.map", mp_time, seq_time))

    if FASTITER_AVAILABLE:
        fi_time, _ = _measure(lambda: par_range(0, n).map(_expensive).sum())
        print(_row("FastIter (threads)", fi_time, seq_time))


def bench_overhead_small(
    pool: multiprocessing.pool.Pool, n: int = 10_000
) -> None:
    """Small dataset — shows spawn/pickle overhead dominates."""
    _header("Small Dataset  [spawn/pickle overhead]", n)
    print("  (Shows that process overhead dominates for small N)")

    seq_time, _ = _measure(lambda: sum(x * x for x in range(n)))
    print(_row("sequential (generator)", seq_time, seq_time))

    chunk = max(1, n // multiprocessing.cpu_count())
    mp_time, _ = _measure(
        lambda: sum(pool.map(_square, range(n), chunksize=chunk))
    )
    print(_row("multiprocessing.Pool.map", mp_time, seq_time))

    if FASTITER_AVAILABLE:
        fi_time, _ = _measure(lambda: par_range(0, n).map(_square).sum())
        print(_row("FastIter (threads)", fi_time, seq_time))


def bench_pickle_cost(pool: multiprocessing.pool.Pool) -> None:
    """
    Isolate raw pickling cost: measure how long it takes to pickle
    a 1M-element list vs simply iterating it.  This is the overhead
    multiprocessing.Pool pays per task batch.
    """
    import pickle

    _header("Raw Pickle Cost  (1M integers)", 1_000_000)
    print("  (Illustrates the serialisation tax on every Pool call)")

    data = list(range(1_000_000))

    iter_time, _ = _measure(lambda: sum(data))
    print(_row("sum(list)  — zero-copy", iter_time, iter_time))

    pickle_time, _ = _measure(lambda: pickle.dumps(data))
    print(_row("pickle.dumps(list)", pickle_time, iter_time))

    roundtrip_time, _ = _measure(lambda: pickle.loads(pickle.dumps(data)))
    print(_row("pickle roundtrip (dumps+loads)", roundtrip_time, iter_time))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    import sys

    gil_status = (
        "disabled"
        if not sys._is_gil_enabled()
        else "ENABLED (FastIter speedups won't apply)"
    )
    ncpus = os.cpu_count() or 4

    print("FastIter vs multiprocessing.Pool Benchmark")
    print("=" * 64)
    print(f"Python   : {sys.version}")
    print(f"GIL      : {gil_status}")
    print(f"CPUs     : {ncpus}")

    if FASTITER_AVAILABLE:
        num_threads = int(os.environ.get("FASTITER_NUM_THREADS", ncpus))
        set_num_threads(num_threads)
        # Warm up the executor before any timed run so the first benchmark
        # doesn't pay the thread-pool creation cost.
        par_range(0, 10_000).map(_square).sum()
        print(f"Threads  : {num_threads} (FastIter)")
    else:
        print("FastIter : not available")

    # Use a fixed pool size matching the thread count for a fair comparison.
    pool_workers = int(os.environ.get("FASTITER_NUM_THREADS", ncpus))
    print(f"Workers  : {pool_workers} (multiprocessing.Pool)")
    print()
    print(
        "Speedup column is relative to the sequential baseline"
        " (higher = faster)."
    )
    print("Values < 1.0x mean slower than sequential.")

    with multiprocessing.Pool(processes=pool_workers) as pool:
        bench_sum_of_squares(pool)
        bench_filter_sum(pool)
        bench_cpu_intensive(pool)
        bench_overhead_small(pool)
        bench_pickle_cost(pool)

    print(f"\n{'=' * 64}")
    print("Notes")
    print(f"{'=' * 64}")
    print(
        "  • Run with `python3.14t` (free-threaded) for real FastIter speedups."
    )
    print("  • multiprocessing results are valid under any Python build.")
    print(
        "  • Pickle cost benchmark isolates serialisation overhead independent"
    )
    print("    of parallelism — this is the tax Pool pays on every task batch.")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    # Guard required by multiprocessing on macOS / Windows (spawn start method).
    multiprocessing.freeze_support()
    main()
