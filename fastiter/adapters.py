"""
Adapters for converting standard Python objects into parallel iterators.

This module provides the ergonomic interface for creating parallel iterators
from common Python data structures.
"""

from collections.abc import Callable, Iterable, Sequence
from typing import TypeVar, overload

from .core import IndexedParallelIterator
from .producers import ListProducer, RangeProducer, TupleProducer
from .protocols import Producer

T = TypeVar("T")
R = TypeVar("R")


class IntoParallelIterator(IndexedParallelIterator[T]):
    """
    Generic parallel iterator created from a producer.

    This wraps a producer and provides all parallel iterator operations.
    """

    def __init__(self, producer: Producer[T]):
        """
        Create a parallel iterator from a producer.

        Args:
            producer: The producer to wrap
        """
        self.producer = producer

    def __len__(self) -> int:
        """Return the number of elements in this iterator."""
        return len(self.producer)

    def with_producer(self, callback: Callable[[Producer[T]], R]) -> R:
        """
        Execute a callback with this iterator's producer.

        Args:
            callback: Function that receives the producer

        Returns:
            The result from the callback
        """
        return callback(self.producer)


class ParallelRange(IndexedParallelIterator[int]):
    """
    Parallel iterator over a range of integers.

    This is analogous to Python's built-in range() but processes elements
    in parallel.
    """

    def __init__(self, start: int, stop: int, step: int = 1):
        """
        Create a parallel range iterator.

        Args:
            start: Starting value (inclusive)
            stop: Ending value (exclusive)
            step: Step size (default 1)
        """
        self.producer = RangeProducer(start, stop, step)

    def __len__(self) -> int:
        """Return the number of elements in this range."""
        return len(self.producer)

    def with_producer(self, callback: Callable[[Producer[int]], R]) -> R:
        """Execute a callback with the range producer."""
        return callback(self.producer)


class ParallelList(IndexedParallelIterator[T]):
    """
    Parallel iterator over a list or sequence.

    This wraps a list, tuple, or other sequence for parallel processing.
    """

    def __init__(self, data: Sequence[T]):
        """
        Create a parallel list iterator.

        Args:
            data: The sequence to iterate over
        """
        self.data = data
        if isinstance(data, tuple):
            self.producer = TupleProducer(data)
        else:
            self.producer = ListProducer(data)

    def __len__(self) -> int:
        """Return the number of elements in this sequence."""
        return len(self.producer)

    def with_producer(self, callback: Callable[[Producer[T]], R]) -> R:
        """Execute a callback with the list producer."""
        return callback(self.producer)


def par_range(start: int, stop: int, step: int = 1) -> ParallelRange:
    """
    Create a parallel range iterator.

    This is the parallel equivalent of Python's range() function.

    Args:
        start: Starting value (inclusive)
        stop: Ending value (exclusive)
        step: Step size (default 1)

    Returns:
        A ParallelRange iterator

    Example:
        >>> from fastiter import par_range
        >>> result = par_range(0, 1000000).map(lambda x: x * 2).sum()
    """
    return ParallelRange(start, stop, step)


@overload
def into_par_iter(data: range) -> ParallelRange: ...


@overload
def into_par_iter[T](data: Iterable[T]) -> IndexedParallelIterator[T]: ...


def into_par_iter[T](
    data: Iterable[T],
) -> ParallelRange | IndexedParallelIterator[T]:
    """
    Convert an iterable into a parallel iterator.

    This provides a convenient way to parallelize operations on standard
    Python data structures.

    Args:
        data: Any iterable (list, tuple, range, etc.)

    Returns:
        A parallel iterator over the data

    Raises:
        TypeError: If the data type is not supported

    Example:
        >>> from fastiter import into_par_iter
        >>> data = [1, 2, 3, 4, 5]
        >>> result = into_par_iter(data).map(lambda x: x ** 2).collect()
    """
    if isinstance(data, range):
        return ParallelRange(data.start, data.stop, data.step)
    elif isinstance(data, list | tuple):
        return ParallelList(data)
    elif isinstance(data, Sequence):
        return ParallelList(data)
    else:
        materialized = list(data)
        return ParallelList(materialized)


def _add_par_iter_method():
    """
    Add par_iter() method to built-in types.

    This is experimental and may not work in all Python implementations.
    """
    try:
        # Try to add method to list
        def par_iter_list(self):
            return ParallelList(self)

        list.par_iter = par_iter_list  # type: ignore[attr-defined]

        # Try to add method to tuple
        def par_iter_tuple(self):
            return ParallelList(self)

        tuple.par_iter = par_iter_tuple  # type: ignore[attr-defined]

    except (TypeError, AttributeError):
        # Built-in types can't be modified in CPython
        # This is expected, just skip
        pass


_add_par_iter_method()
