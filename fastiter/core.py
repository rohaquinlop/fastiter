"""
Core parallel iterator implementations.

This module contains the main ParallelIterator and IndexedParallelIterator
classes that provide parallel versions of common iterator operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from .bridge import bridge
from .consumers import (
    CollectConsumer,
    CountConsumer,
    FilterConsumer,
    FoldConsumer,
    ForEachConsumer,
    MapConsumer,
    ReduceConsumer,
    SumConsumer,
)
from .protocols import Consumer, Producer

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")


class ParallelIterator[T](ABC):
    """
    Base class for parallel iterators.

    A parallel iterator represents a sequence of elements that can be
    processed in parallel. It provides methods like map, filter, reduce,
    etc. that execute in parallel across multiple threads.
    """

    @abstractmethod
    def drive_unindexed(self, consumer: Consumer[T, R]) -> R:
        """
        Internal method to drive iteration with a consumer.

        This is the core method that subclasses must implement to enable
        parallel iteration.

        Args:
            consumer: The consumer that will process elements

        Returns:
            The result from the consumer
        """
        ...

    def map(self, func: Callable[[T], U]) -> ParallelIterator[U]:
        """
        Apply a function to each element in parallel.

        Args:
            func: Function to apply to each element

        Returns:
            A new parallel iterator of transformed elements
        """
        return MapIterator(self, func)

    def filter(self, predicate: Callable[[T], bool]) -> ParallelIterator[T]:
        """
        Filter elements based on a predicate in parallel.

        Args:
            predicate: Function that returns True for elements to keep

        Returns:
            A new parallel iterator of filtered elements
        """
        return FilterIterator(self, predicate)

    def fold(
        self, identity: Callable[[], R], fold_op: Callable[[R, T], R]
    ) -> ParallelIterator[R]:
        """
        Reduce chunks in parallel, then return the per-chunk results.

        Args:
            identity: Function that creates the initial accumulator value
            fold_op: Function to fold an element into the accumulator

        Returns:
            A parallel iterator of fold results (one per chunk)
        """
        return FoldIterator(self, identity, fold_op)

    def reduce(
        self, identity: Callable[[], R], reduce_op: Callable[[R, R], R]
    ) -> R:
        """
        Reduce all elements to a single value in parallel.

        Args:
            identity: Function that creates the initial/identity value
            reduce_op: Associative function to combine two values

        Returns:
            The final reduced value
        """
        consumer = ReduceConsumer(identity, reduce_op)
        return self.drive_unindexed(consumer)

    def for_each(self, func: Callable[[T], None]) -> None:
        """
        Execute a function on each element in parallel.

        Args:
            func: Function to execute for each element
        """
        consumer = ForEachConsumer(func)
        self.drive_unindexed(consumer)

    def collect(self) -> list[T]:
        """
        Collect all elements into a list.

        The order of elements may not match the original sequence order
        unless this is an IndexedParallelIterator.

        Returns:
            A list containing all elements
        """
        consumer = CollectConsumer()
        return self.drive_unindexed(consumer)

    def sum(self) -> T:
        """
        Sum all elements in parallel.

        Returns:
            The sum of all elements
        """
        consumer = SumConsumer()
        return self.drive_unindexed(consumer)

    def count(self) -> int:
        """
        Count the number of elements in parallel.

        Returns:
            The total count of elements
        """
        consumer = CountConsumer()
        return self.drive_unindexed(consumer)

    def min(self, key: Callable[[T], Any] | None = None) -> T | None:
        """
        Find the minimum element in parallel.

        Args:
            key: Optional key function for comparison

        Returns:
            The minimum element, or None if iterator is empty
        """
        if key is None:

            def identity():
                return None

            def reduce_op(a, b):
                return a if b is None else (b if a is None else min(a, b))
        else:

            def identity():
                return None

            def reduce_op(a, b):
                return (
                    a
                    if b is None
                    else (b if a is None else (a if key(a) <= key(b) else b))
                )

        return self.reduce(identity, reduce_op)

    def max(self, key: Callable[[T], Any] | None = None) -> T | None:
        """
        Find the maximum element in parallel.

        Args:
            key: Optional key function for comparison

        Returns:
            The maximum element, or None if iterator is empty
        """
        if key is None:

            def identity():
                return None

            def reduce_op(a, b):
                return a if b is None else (b if a is None else max(a, b))
        else:

            def identity():
                return None

            def reduce_op(a, b):
                return (
                    a
                    if b is None
                    else (b if a is None else (a if key(a) >= key(b) else b))
                )

        return self.reduce(identity, reduce_op)

    def any(self, predicate: Callable[[T], bool] | None = None) -> bool:
        """
        Check if any element matches the predicate.

        Args:
            predicate: Optional predicate function (defaults to bool)

        Returns:
            True if any element matches, False otherwise
        """
        if predicate is None:
            predicate = bool

        def identity():
            return False

        def reduce_op(a, b):
            return a or b

        return self.map(predicate).reduce(identity, reduce_op)

    def all(self, predicate: Callable[[T], bool] | None = None) -> bool:
        """
        Check if all elements match the predicate.

        Args:
            predicate: Optional predicate function (defaults to bool)

        Returns:
            True if all elements match, False otherwise
        """
        if predicate is None:
            predicate = bool

        def identity():
            return True

        def reduce_op(a, b):
            return a and b

        return self.map(predicate).reduce(identity, reduce_op)


class IndexedParallelIterator(ParallelIterator[T], ABC):
    """
    A parallel iterator with known length and random access.

    Indexed parallel iterators can be split at arbitrary positions and
    provide better performance for ordered operations.
    """

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of elements in this iterator."""
        ...

    @abstractmethod
    def with_producer(self, callback: Callable[[Producer[T]], R]) -> R:
        """
        Execute a callback with a producer for this iterator.

        Args:
            callback: Function that receives a producer and returns a result

        Returns:
            The result from the callback
        """
        ...

    def drive(self, consumer: Consumer[T, R]) -> R:
        """
        Drive this iterator with an indexed consumer.

        Args:
            consumer: The consumer that will process elements

        Returns:
            The result from the consumer
        """
        return self.with_producer(lambda producer: bridge(producer, consumer))

    def drive_unindexed(self, consumer: Consumer[T, R]) -> R:
        """
        Drive this iterator with an unindexed consumer.

        For indexed iterators, this delegates to the indexed drive method.

        Args:
            consumer: The consumer that will process elements

        Returns:
            The result from the consumer
        """
        return self.drive(consumer)


# Concrete iterator adapters


class MapIterator[T, U](ParallelIterator[U]):
    """Parallel iterator that maps a function over elements."""

    def __init__(self, base: ParallelIterator[T], func: Callable[[T], U]):
        self.base = base
        self.func = func

    def drive_unindexed(self, consumer: Consumer[U, R]) -> R:
        map_consumer = MapConsumer(consumer, self.func)
        return self.base.drive_unindexed(map_consumer)


class FilterIterator(ParallelIterator[T]):
    """Parallel iterator that filters elements by a predicate."""

    def __init__(
        self, base: ParallelIterator[T], predicate: Callable[[T], bool]
    ):
        self.base = base
        self.predicate = predicate

    def drive_unindexed(self, consumer: Consumer[T, R]) -> R:
        filter_consumer = FilterConsumer(consumer, self.predicate)
        return self.base.drive_unindexed(filter_consumer)


class FoldIterator[T, R](ParallelIterator[R]):
    """Parallel iterator that folds chunks of elements."""

    def __init__(
        self,
        base: ParallelIterator[T],
        identity: Callable[[], R],
        fold_op: Callable[[R, T], R],
    ):
        self.base = base
        self.identity = identity
        self.fold_op = fold_op

    def drive_unindexed(self, consumer: Consumer[R, Any]) -> Any:
        fold_consumer = FoldConsumer(consumer, self.identity, self.fold_op)
        return self.base.drive_unindexed(fold_consumer)
