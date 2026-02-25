"""
Benchmarks comparing FastIter with standard Python iteration.

Run this with Python 3.14+ in free-threaded mode for best results:
    uv run --python 3.14t python benchmarks/benchmark.py

Each benchmark shows two sequential baselines:
  - generator expression  e.g. sum(x*x for x in range(N))
  - map/filter chain      e.g. sum(map(fn, range(N)))

The generator expression fuses multiple stages into one tight loop and
benefits from per-element __next__ call optimisations.  The map/filter chain
is cheaper to set up and avoids generator frame overhead; it represents the
best single-threaded built-in pipeline for the same operation.  Showing both
gives a fuller picture of where FastIter sits.

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


def _one(_: int) -> int:
    return 1


# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------


def benchmark(
    name: str,
    parallel_fn: Callable[[], Any],
    baselines: dict[str, Callable[[], Any]],
    n: int | None = None,
    tip: str = "FastIter shines on larger datasets",
    iterations: int = 3,
) -> float:
    """
    Benchmark a parallel function against one or more sequential baselines.

    Args:
        name: Name of the benchmark
        parallel_fn: Function using parallel iteration
        baselines: Ordered dict of label -> sequential function
        n: Dataset size, displayed in the header when provided
        tip: Shown when FastIter loses, explaining why and what to do instead
        iterations: Number of timed runs per function

    Returns:
        Speedup relative to the first baseline (for summary statistics)
    """
    header = f"Benchmark: {name}"
    if n is not None:
        header += f"  [N={n:,}]"
    print(f"\n{'=' * 60}")
    print(header)
    print(f"{'=' * 60}")

    # Warm-up
    parallel_fn()
    for fn in baselines.values():
        fn()

    # Time each sequential baseline first
    baseline_results: list[tuple[str, float]] = []
    for label, fn in baselines.items():
        seq_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            seq_times.append(time.perf_counter() - start)
        baseline_results.append((label, sum(seq_times) / len(seq_times)))

    # Time parallel
    parallel_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        parallel_fn()
        parallel_times.append(time.perf_counter() - start)
    avg_parallel = sum(parallel_times) / len(parallel_times)

    # Print baselines first, each annotated relative to FastIter
    for label, avg_seq in baseline_results:
        speedup = avg_seq / avg_parallel
        if speedup >= 1.0:
            note = f"{speedup:.2f}x slower than FastIter"
        else:
            note = f"{1 / speedup:.2f}x faster than FastIter"
        print(f"  {label:<32} {avg_seq:.4f}s  ({note})")

    # Separator + FastIter result at the bottom
    print(f"  {'─' * 57}")
    first_speedup = (
        baseline_results[0][1] / avg_parallel if baseline_results else 1.0
    )
    if first_speedup >= 1.0:
        verdict = f"<-- {first_speedup:.2f}x faster than baseline"
    else:
        verdict = f"<-- {1 / first_speedup:.2f}x slower  (tip: {tip})"
    print(f"  {'FastIter (parallel)':<32} {avg_parallel:.4f}s  {verdict}")

    return first_speedup


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------


def bench_sum_of_squares():
    """Benchmark: Sum of squares."""

    def _run(N: int) -> float:
        return benchmark(
            "Sum of Squares",
            lambda: par_range(0, N).map(_square).sum(),
            {
                "generator expression": lambda: sum(x * x for x in range(N)),
                "sum(map(fn, range))": lambda: sum(map(_square, range(N))),
            },
            n=N,
        )

    _run(10_000)
    return _run(10_000_000)


def bench_filter_sum():
    """Benchmark: Filter and sum."""

    def _run(N: int) -> float:
        return benchmark(
            "Filter Even Numbers and Sum",
            lambda: par_range(0, N).filter(_is_even).sum(),
            {
                "generator expression": lambda: sum(
                    x for x in range(N) if x % 2 == 0
                ),
                "sum(filter(fn, range))": lambda: sum(
                    filter(_is_even, range(N))
                ),
            },
            n=N,
        )

    _run(10_000)
    return _run(10_000_000)


def bench_complex_pipeline():
    """Benchmark: Complex multi-stage pipeline."""

    def _run(N: int) -> float:
        def map_filter_chain():
            return sum(
                map(_increment, filter(_divisible_by_3, map(_double, range(N))))
            )

        return benchmark(
            "Complex Pipeline (map→filter→map→sum)",
            lambda: (
                par_range(0, N)
                .map(_double)
                .filter(_divisible_by_3)
                .map(_increment)
                .sum()
            ),
            {
                "generator expression": lambda: sum(
                    (x * 2) + 1 for x in range(N) if (x * 2) % 3 == 0
                ),
                "map/filter chain": map_filter_chain,
            },
            n=N,
        )

    _run(10_000)
    return _run(5_000_000)


def bench_list_processing():
    """Benchmark: Processing large lists."""

    def _run(N: int) -> float:
        data = list(range(N))

        def map_filter_chain():
            return sum(map(_one, filter(_is_even, map(_square_of_item, data))))

        return benchmark(
            "List Processing (map→filter→count)",
            lambda: into_par_iter(data)
            .map(_square_of_item)
            .filter(_is_even)
            .count(),
            {
                "generator expression": lambda: sum(
                    1 for x in data if (x**2) % 2 == 0
                ),
                "map/filter chain": map_filter_chain,
            },
            n=N,
        )

    _run(10_000)
    return _run(5_000_000)


def bench_reduce():
    """Benchmark: Custom reduce operation."""

    def _run(N: int) -> float:
        return benchmark(
            "Custom Reduce",
            lambda: par_range(1, N).reduce(_zero, _add),
            {
                "generator expression": lambda: sum(x for x in range(1, N)),
                "sum(range)": lambda: sum(range(1, N)),
            },
            n=N,
        )

    _run(10_000)
    return _run(1_000_000)


def bench_min_max():
    """Benchmark: Finding min and max over a range."""

    def _run(N: int) -> float:
        return benchmark(
            "Min/Max",
            lambda: (par_range(0, N).min(), par_range(0, N).max()),
            {
                "generator expression": lambda: (
                    min(x for x in range(N)),
                    max(x for x in range(N)),
                ),
                "min/max(range)": lambda: (min(range(N)), max(range(N))),
            },
            n=N,
        )

    _run(10_000)
    return _run(10_000_000)


def bench_count():
    """Benchmark: Counting elements."""

    def _run(N: int) -> float:
        return benchmark(
            "Count Filtered Elements",
            lambda: par_range(0, N).filter(_divisible_by_7).count(),
            {
                "generator expression": lambda: sum(
                    1 for x in range(N) if x % 7 == 0
                ),
                "sum(map(_one, filter(...)))": lambda: sum(
                    map(_one, filter(_divisible_by_7, range(N)))
                ),
            },
            n=N,
        )

    _run(10_000)
    return _run(10_000_000)


def bench_known_limitations():
    """
    Benchmarks that demonstrate the two structural cases where FastIter
    is the wrong tool — independent of how many threads you throw at it.
    """
    print(f"\n{'#' * 60}")
    print("# When NOT to use FastIter")
    print(f"{'#' * 60}")
    print(
        "FastIter adds a parallel work-stealing layer on top of CPython.\n"
        "That overhead only pays off when two conditions are met:\n"
        "  1. Per-element computation is meaningful (not just a C builtin)\n"
        "  2. N is large enough that parallelism amortises the setup cost\n"
        "\n"
        "The cases below are structural mismatches — not just unlucky N values."
    )

    # ------------------------------------------------------------------
    # [1] C-optimised builtins: no Python work per element
    # ------------------------------------------------------------------
    print(
        "\n  [1] C-optimised aggregation\n"
        "      sum(range(N)) never calls a Python function per element:\n"
        "      range is a C iterator and sum() accumulates in C.\n"
        "      FastIter's reduce(_zero, _add) calls the Python _add function\n"
        "      for every element — those Python-level calls cannot be elided\n"
        "      by threading, so the C builtin wins regardless of N."
    )
    N = 10_000_000
    benchmark(
        "reduce(_add) vs sum(range) — C builtin always wins",
        lambda: par_range(0, N).reduce(_zero, _add),
        {"sum(range(N))  [C builtin]": lambda: sum(range(N))},
        n=N,
        tip=(
            "when a C builtin covers the whole operation, use it directly"
            " — no Python-level parallelism can compete"
        ),
    )

    # ------------------------------------------------------------------
    # [2] Small datasets: thread setup cost dominates
    # ------------------------------------------------------------------
    print(
        "\n  [2] Small datasets\n"
        "      Thread pool setup, work splitting, and result merging\n"
        "      cost roughly 0.1–1 ms regardless of N.\n"
        "      Rule of thumb: N < 500k → use sequential iteration."
    )
    N_small = 10_000
    benchmark(
        "Sum of squares — N too small for parallelism",
        lambda: par_range(0, N_small).map(_square).sum(),
        {
            "sum(x*x for x in range(N))": lambda: sum(
                x * x for x in range(N_small)
            )
        },
        n=N_small,
        tip=(
            "thread setup cost (~1 ms) dominates;"
            " use sequential iteration for N < ~500k"
        ),
    )


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
    print("Baselines: generator expression  vs  map/filter chain.")
    print("Run with Python 3.14+ in free-threaded mode for real speedups.")
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

    # Show structural cases where FastIter is the wrong choice.
    # These are intentional losses — not included in the summary.
    bench_known_limitations()

    # Summary (speedup relative to generator expression baseline)
    print(f"\n{'=' * 60}")
    print("Summary  (speedup vs generator expression baseline)")
    print(f"{'=' * 60}")
    avg_speedup = sum(speedups) / len(speedups)
    print(f"Average speedup: {avg_speedup:.2f}x")
    print(f"Best speedup:    {max(speedups):.2f}x")
    print(f"Worst speedup:   {min(speedups):.2f}x")


if __name__ == "__main__":
    main()
