"""
Benchmarks comparing FastIter with standard Python iteration.

Run this with Python 3.14+ in free-threaded mode for best results:
    uv run --python 3.14t python benchmarks/benchmark.py

NOTE: worker functions must be defined at module level, not inside closures.
In free-threaded CPython (3.14t), calling a closure from multiple threads
causes contention on the frame's cell objects, serialising execution and
erasing all parallelism gains. Module-level functions share no mutable cell
state and scale correctly across threads.
"""

import os
import time
from collections.abc import Callable
from typing import Any

from fastiter import into_par_iter, par_range, set_num_threads

# ---------------------------------------------------------------------------
# Module-level worker functions (required for correct free-threaded scaling)
# ---------------------------------------------------------------------------


def _square(x: int) -> int:
    return x * x


def _double(x: int) -> int:
    return x * 2


def _increment(x: int) -> int:
    return x + 1


def _square_of_item(x: int) -> int:
    return x**2


def _is_even(x: int) -> bool:
    return x % 2 == 0


def _divisible_by_3(x: int) -> bool:
    return x % 3 == 0


def _divisible_by_7(x: int) -> bool:
    return x % 7 == 0


def _add(a: int, b: int) -> int:
    return a + b


def _zero() -> int:
    return 0


# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------


def benchmark(
    name: str,
    parallel_fn: Callable[[], Any],
    sequential_fn: Callable[[], Any],
    iterations: int = 3,
):
    """
    Benchmark a parallel function against its sequential equivalent.

    Args:
        name: Name of the benchmark
        parallel_fn: Function using parallel iteration
        sequential_fn: Function using sequential iteration
        iterations: Number of times to run each function
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: {name}")
    print(f"{'=' * 60}")

    # Warm-up
    parallel_fn()
    sequential_fn()

    # Benchmark parallel
    parallel_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        _result_parallel = parallel_fn()
        end = time.perf_counter()
        parallel_times.append(end - start)

    # Benchmark sequential
    sequential_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        _result_sequential = sequential_fn()
        end = time.perf_counter()
        sequential_times.append(end - start)

    # Calculate statistics
    avg_parallel = sum(parallel_times) / len(parallel_times)
    avg_sequential = sum(sequential_times) / len(sequential_times)
    speedup = avg_sequential / avg_parallel

    print(f"Parallel (avg):   {avg_parallel:.4f} seconds")
    print(f"Sequential (avg): {avg_sequential:.4f} seconds")
    print(f"Speedup:          {speedup:.2f}x")

    return speedup


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------


def bench_sum_of_squares():
    """Benchmark: Sum of squares."""
    N = 10_000_000

    def parallel():
        return par_range(0, N).map(_square).sum()

    def sequential():
        return sum(x * x for x in range(N))

    return benchmark("Sum of Squares", parallel, sequential)


def bench_filter_sum():
    """Benchmark: Filter and sum."""
    N = 10_000_000

    def parallel():
        return par_range(0, N).filter(_is_even).sum()

    def sequential():
        return sum(x for x in range(N) if x % 2 == 0)

    return benchmark("Filter Even Numbers and Sum", parallel, sequential)


def bench_complex_pipeline():
    """Benchmark: Complex multi-stage pipeline."""
    N = 5_000_000

    def parallel():
        return (
            par_range(0, N)
            .map(_double)
            .filter(_divisible_by_3)
            .map(_increment)
            .sum()
        )

    def sequential():
        return sum((x * 2) + 1 for x in range(N) if (x * 2) % 3 == 0)

    return benchmark("Complex Pipeline", parallel, sequential)


def bench_list_processing():
    """Benchmark: Processing large lists."""
    N = 5_000_000
    data = list(range(N))

    def parallel():
        return into_par_iter(data).map(_square_of_item).filter(_is_even).count()

    def sequential():
        return sum(1 for x in data if (x**2) % 2 == 0)

    return benchmark("List Processing", parallel, sequential)


def bench_reduce():
    """Benchmark: Custom reduce operation."""
    N = 1_000_000

    def parallel():
        return par_range(1, N).reduce(_zero, _add)

    def sequential():
        result = 0
        for x in range(1, N):
            result = result + x
        return result

    return benchmark("Custom Reduce", parallel, sequential)


def bench_min_max():
    """Benchmark: Finding min and max over a range."""
    N = 10_000_000

    def parallel():
        return par_range(0, N).min(), par_range(0, N).max()

    def sequential():
        return min(range(N)), max(range(N))

    return benchmark("Min/Max", parallel, sequential)


def bench_count():
    """Benchmark: Counting elements."""
    N = 10_000_000

    def parallel():
        return par_range(0, N).filter(_divisible_by_7).count()

    def sequential():
        return sum(1 for x in range(N) if x % 7 == 0)

    return benchmark("Count Filtered Elements", parallel, sequential)


def scaling_benchmark():
    """Benchmark with different thread counts."""
    print(f"\n{'=' * 60}")
    print("Thread Scaling Benchmark")
    print(f"{'=' * 60}")

    N = 10_000_000
    thread_counts = [1, 2, 4, 8, 16]
    times = []

    for num_threads in thread_counts:
        set_num_threads(num_threads)
        # Warm up the newly created executor before timing.
        par_range(0, 10_000).map(_square).sum()

        # Run benchmark
        iterations = 3
        run_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            _result = par_range(0, N).map(_square).sum()
            end = time.perf_counter()
            run_times.append(end - start)

        avg_time = sum(run_times) / len(run_times)
        times.append(avg_time)
        print(f"Threads: {num_threads:2d}  Time: {avg_time:.4f}s")

    # Calculate speedups
    print(f"\n{'=' * 60}")
    print("Speedup vs 1 thread:")
    baseline = times[0]
    for i, num_threads in enumerate(thread_counts):
        speedup = baseline / times[i]
        print(f"Threads: {num_threads:2d}  Speedup: {speedup:.2f}x")


def main():
    """Run all benchmarks."""
    print("FastIter Benchmarks")
    print("=" * 60)
    print("These benchmarks compare parallel vs sequential execution.")
    print("Run with Python 3.14+ in free-threaded mode for best results.")
    print("=" * 60)

    num_threads = int(
        os.environ.get("FASTITER_NUM_THREADS", os.cpu_count() or 4)
    )
    set_num_threads(num_threads)
    print(f"\nUsing {num_threads} threads")

    # Thread scaling runs first so its executor teardown loop doesn't affect
    # the main benchmarks that follow.
    scaling_benchmark()

    # Restore the intended thread count and warm up the executor before
    # the first timed benchmark.
    set_num_threads(num_threads)
    par_range(0, 10_000).map(_square).sum()

    # Run benchmarks
    speedups = []
    speedups.append(bench_sum_of_squares())
    speedups.append(bench_filter_sum())
    speedups.append(bench_complex_pipeline())
    speedups.append(bench_list_processing())
    speedups.append(bench_reduce())
    speedups.append(bench_min_max())
    speedups.append(bench_count())

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    avg_speedup = sum(speedups) / len(speedups)
    print(f"Average speedup: {avg_speedup:.2f}x")
    print(f"Best speedup:    {max(speedups):.2f}x")
    print(f"Worst speedup:   {min(speedups):.2f}x")


if __name__ == "__main__":
    main()
