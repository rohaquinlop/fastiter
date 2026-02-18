"""
Consumer implementations for various parallel operations.

Consumers process elements produced by parallel iterators and combine
results from different threads.
"""

import threading
from collections.abc import Callable, Iterator
from typing import TypeVar

from .protocols import Consumer

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")


class MapConsumer[T, U, R]:
    """
    Consumer that maps a function over elements
    before passing to another consumer.
    """

    def __init__(self, base: Consumer[U, R], func: Callable[[T], U]):
        self.base = base
        self.func = func

    def consume_iter(self, iterator: Iterator[T]) -> R:
        """Map function over iterator elements then consume with base."""
        mapped = (self.func(item) for item in iterator)
        return self.base.consume_iter(mapped)

    def split(self) -> tuple[MapConsumer[T, U, R], MapConsumer[T, U, R]]:
        """Split by splitting the base consumer."""
        left_base, right_base = self.base.split()
        return (
            MapConsumer(left_base, self.func),
            MapConsumer(right_base, self.func),
        )

    def reduce(self, left: R, right: R) -> R:
        """Reduce by delegating to base consumer."""
        return self.base.reduce(left, right)


class FilterConsumer[T, R]:
    """Consumer that filters elements before passing to another consumer."""

    def __init__(self, base: Consumer[T, R], predicate: Callable[[T], bool]):
        self.base = base
        self.predicate = predicate

    def consume_iter(self, iterator: Iterator[T]) -> R:
        """Filter iterator elements then consume with base."""
        filtered = (item for item in iterator if self.predicate(item))
        return self.base.consume_iter(filtered)

    def split(self) -> tuple[FilterConsumer[T, R], FilterConsumer[T, R]]:
        """Split by splitting the base consumer."""
        left_base, right_base = self.base.split()
        return (
            FilterConsumer(left_base, self.predicate),
            FilterConsumer(right_base, self.predicate),
        )

    def reduce(self, left: R, right: R) -> R:
        """Reduce by delegating to base consumer."""
        return self.base.reduce(left, right)


class ReduceConsumer[T]:
    """Consumer that reduces elements to a single value."""

    def __init__(
        self, identity: Callable[[], T], reduce_op: Callable[[T, T], T]
    ):
        self.identity = identity
        self.reduce_op = reduce_op

    def consume_iter(self, iterator: Iterator[T]) -> T:
        """Reduce all elements using the reduce operation."""
        accumulator = self.identity()
        for item in iterator:
            accumulator = self.reduce_op(accumulator, item)
        return accumulator

    def split(self) -> tuple[ReduceConsumer[T], ReduceConsumer[T]]:
        """
        Split by creating two independent consumers with the same operations.
        """
        return (
            ReduceConsumer(self.identity, self.reduce_op),
            ReduceConsumer(self.identity, self.reduce_op),
        )

    def reduce(self, left: T, right: T) -> T:
        """Combine two reduced values."""
        return self.reduce_op(left, right)


class FoldConsumer[T, U, R]:
    """Consumer that folds elements and passes results to another consumer."""

    def __init__(
        self,
        base: Consumer[U, R],
        identity: Callable[[], U],
        fold_op: Callable[[U, T], U],
    ):
        self.base = base
        self.identity = identity
        self.fold_op = fold_op

    def consume_iter(self, iterator: Iterator[T]) -> R:
        """Fold elements then pass the result to base consumer."""
        accumulator = self.identity()
        for item in iterator:
            accumulator = self.fold_op(accumulator, item)
        # Pass the folded result as a single-item iterator to base
        return self.base.consume_iter(iter([accumulator]))

    def split(self) -> tuple[FoldConsumer[T, U, R], FoldConsumer[T, U, R]]:
        """Split by splitting the base consumer."""
        left_base, right_base = self.base.split()
        return (
            FoldConsumer(left_base, self.identity, self.fold_op),
            FoldConsumer(right_base, self.identity, self.fold_op),
        )

    def reduce(self, left: R, right: R) -> R:
        """Reduce by delegating to base consumer."""
        return self.base.reduce(left, right)


class CollectConsumer[T]:
    """Consumer that collects all elements into a list."""

    def __init__(self):
        self.lock = threading.Lock()

    def consume_iter(self, iterator: Iterator[T]) -> list[T]:
        """Collect all elements into a list."""
        return list(iterator)

    def split(self) -> tuple[CollectConsumer[T], CollectConsumer[T]]:
        """Split by creating two independent collectors."""
        return (CollectConsumer(), CollectConsumer())

    def reduce(self, left: list[T], right: list[T]) -> list[T]:
        """Combine two lists by concatenation."""
        # For better performance, extend left with right in-place
        left.extend(right)
        return left


class ForEachConsumer[T]:
    """Consumer that executes a function on each element."""

    def __init__(self, func: Callable[[T], None]):
        self.func = func

    def consume_iter(self, iterator: Iterator[T]) -> None:
        """Execute function on each element."""
        for item in iterator:
            self.func(item)
        return None

    def split(self) -> tuple[ForEachConsumer[T], ForEachConsumer[T]]:
        """Split by creating two consumers with the same function."""
        return (ForEachConsumer(self.func), ForEachConsumer(self.func))

    def reduce(self, left: None, right: None) -> None:
        """Nothing to reduce for for_each."""
        return None


class SumConsumer[T]:
    """Consumer that sums numeric elements."""

    def consume_iter(self, iterator: Iterator[T]) -> T:
        """Sum all elements."""
        return sum(iterator)  # type: ignore[arg-type, return-value]

    def split(self) -> tuple[SumConsumer[T], SumConsumer[T]]:
        """Split by creating two independent sum consumers."""
        return (SumConsumer(), SumConsumer())

    def reduce(self, left: T, right: T) -> T:
        """Combine two sums."""
        return left + right  # type: ignore[operator]


class CountConsumer[T]:
    """Consumer that counts elements."""

    def consume_iter(self, iterator: Iterator[T]) -> int:
        """Count all elements."""
        count = 0
        for _ in iterator:
            count += 1
        return count

    def split(self) -> tuple[CountConsumer[T], CountConsumer[T]]:
        """Split by creating two independent count consumers."""
        return (CountConsumer(), CountConsumer())

    def reduce(self, left: int, right: int) -> int:
        """Combine two counts."""
        return left + right


class MinConsumer[T]:
    """Consumer that finds the minimum element using the C-level min() builtin.

    Using min(iterator) per chunk is ~7x faster than a Python reduce loop
    with per-element None checks, because the builtin iterates entirely in C.
    The None sentinel is only used in reduce() to combine chunk results.
    """

    def consume_iter(self, iterator: Iterator[T]) -> T | None:
        return min(iterator, default=None)  # type: ignore[type-var]

    def split(self) -> tuple[MinConsumer[T], MinConsumer[T]]:
        return (MinConsumer(), MinConsumer())

    def reduce(self, left: T | None, right: T | None) -> T | None:
        if left is None:
            return right
        if right is None:
            return left
        return left if left <= right else right  # type: ignore[operator]


class MinKeyConsumer[T]:
    """Consumer that finds the minimum element by a key function."""

    __slots__ = ("key",)

    def __init__(self, key: Callable[[T], Any]) -> None:
        self.key = key

    def consume_iter(self, iterator: Iterator[T]) -> T | None:
        return min(iterator, key=self.key, default=None)  # type: ignore[type-var]

    def split(self) -> tuple[MinKeyConsumer[T], MinKeyConsumer[T]]:
        return (MinKeyConsumer(self.key), MinKeyConsumer(self.key))

    def reduce(self, left: T | None, right: T | None) -> T | None:
        if left is None:
            return right
        if right is None:
            return left
        return left if self.key(left) <= self.key(right) else right


class MaxConsumer[T]:
    """Consumer that finds the maximum element using the C-level max() builtin."""

    def consume_iter(self, iterator: Iterator[T]) -> T | None:
        return max(iterator, default=None)  # type: ignore[type-var]

    def split(self) -> tuple[MaxConsumer[T], MaxConsumer[T]]:
        return (MaxConsumer(), MaxConsumer())

    def reduce(self, left: T | None, right: T | None) -> T | None:
        if left is None:
            return right
        if right is None:
            return left
        return left if left >= right else right  # type: ignore[operator]


class MaxKeyConsumer[T]:
    """Consumer that finds the maximum element by a key function."""

    __slots__ = ("key",)

    def __init__(self, key: Callable[[T], Any]) -> None:
        self.key = key

    def consume_iter(self, iterator: Iterator[T]) -> T | None:
        return max(iterator, key=self.key, default=None)  # type: ignore[type-var]

    def split(self) -> tuple[MaxKeyConsumer[T], MaxKeyConsumer[T]]:
        return (MaxKeyConsumer(self.key), MaxKeyConsumer(self.key))

    def reduce(self, left: T | None, right: T | None) -> T | None:
        if left is None:
            return right
        if right is None:
            return left
        return left if self.key(left) >= self.key(right) else right
