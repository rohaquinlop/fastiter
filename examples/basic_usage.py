"""
Basic usage examples for FastIter.

This demonstrates the core functionality of the parallel iterators library.
"""

from fastiter import into_par_iter, par_range, set_num_threads


def example_map_reduce():
    """Example: Map and reduce operations."""
    print("=== Map and Reduce Example ===")

    # Sum of squares from 0 to 999,999
    result = par_range(0, 1_000_000).map(lambda x: x * x).sum()
    print(f"Sum of squares 0-999,999: {result}")

    # Using custom reduce
    product = par_range(1, 11).reduce(lambda: 1, lambda a, b: a * b)
    print(f"Product of 1-10: {product}")


def example_filter():
    """Example: Filtering elements."""
    print("\n=== Filter Example ===")

    # Count even numbers
    count = par_range(0, 1_000_000).filter(lambda x: x % 2 == 0).count()
    print(f"Count of even numbers 0-999,999: {count}")

    # Sum of numbers divisible by 3
    total = par_range(0, 10_000).filter(lambda x: x % 3 == 0).sum()
    print(f"Sum of numbers divisible by 3 (0-9,999): {total}")


def example_complex_pipeline():
    """Example: Complex pipeline with multiple operations."""
    print("\n=== Complex Pipeline Example ===")

    # Find the sum of squares of even numbers
    result = (
        par_range(0, 100_000)
        .filter(lambda x: x % 2 == 0)
        .map(lambda x: x * x)
        .sum()
    )
    print(f"Sum of squares of even numbers: {result}")

    # Chain multiple transformations
    result = (
        par_range(1, 1001)
        .map(lambda x: x * 2)
        .filter(lambda x: x % 3 == 0)
        .map(lambda x: x + 1)
        .count()
    )
    print(f"Count after transformations: {result}")


def example_lists():
    """Example: Working with lists."""
    print("\n=== List Example ===")

    data = list(range(10_000))

    # Process a list in parallel
    result = (
        into_par_iter(data)
        .map(lambda x: x**2)
        .filter(lambda x: x > 1000)
        .collect()
    )
    print(f"Number of squared values > 1000: {len(result)}")

    # Work with strings
    words = ["hello", "world", "parallel", "iterators", "python"]
    lengths = into_par_iter(words).map(len).collect()
    print(f"Word lengths: {lengths}")


def example_min_max():
    """Example: Finding min and max."""
    print("\n=== Min/Max Example ===")

    numbers = list(range(10_000))

    # Simple min/max
    minimum = into_par_iter(numbers).min()
    maximum = into_par_iter(numbers).max()
    print(f"Min: {minimum}, Max: {maximum}")

    # Min/max with key function
    words = ["a", "abc", "ab", "abcdef", "abcde"]
    longest = into_par_iter(words).max(key=len)
    shortest = into_par_iter(words).min(key=len)
    print(f"Shortest word: {shortest}, Longest word: {longest}")


def example_any_all():
    """Example: Any and all operations."""
    print("\n=== Any/All Example ===")

    # Check if any number is divisible by 7
    has_seven = par_range(1, 100).any(lambda x: x % 7 == 0)
    print(f"Any number divisible by 7 (1-99): {has_seven}")

    # Check if all numbers are positive
    all_positive = par_range(1, 1000).all(lambda x: x > 0)
    print(f"All numbers positive (1-999): {all_positive}")


def example_for_each():
    """Example: Side effects with for_each."""
    print("\n=== For Each Example ===")

    # Note: for_each with shared state requires synchronization
    # This is just for demonstration
    def process(x):
        if x % 1000 == 0:
            print(f"Processing: {x}")

    par_range(0, 10_000).for_each(process)


def example_thread_configuration():
    """Example: Configuring thread pool."""
    print("\n=== Thread Configuration Example ===")

    # Set number of threads
    set_num_threads(8)
    print("Set thread count to 8")

    result = par_range(0, 1_000_000).map(lambda x: x * 2).sum()
    print(f"Result with 8 threads: {result}")

    # You can also set via environment variable:
    # export FASTITER_NUM_THREADS=8


def main():
    """Run all examples."""
    print("FastIter - Parallel Iterators for Python 3.14+\n")

    example_map_reduce()
    example_filter()
    example_complex_pipeline()
    example_lists()
    example_min_max()
    example_any_all()
    example_for_each()
    example_thread_configuration()

    print("\n=== All Examples Complete ===")


if __name__ == "__main__":
    main()
