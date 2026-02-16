"""
Core protocol definitions for parallel iterators.

These protocols define the interface that parallel iterators must implement,
following a design inspired by Rust's Rayon library.
"""

from abc import abstractmethod
from collections.abc import Iterator
from typing import Protocol, TypeVar

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)  # Covariant for Producer (output only)
T_contra = TypeVar(
    "T_contra", contravariant=True
)  # Contravariant for Consumer (input only)
U = TypeVar("U")
R = TypeVar("R")


class Consumer(Protocol[T_contra, R]):
    """
    A consumer processes elements and produces a result.

    Consumers can be split to process work in parallel, and their results
    can be reduced back together.
    """

    @abstractmethod
    def consume_iter(self, iterator: Iterator[T_contra]) -> R:
        """
        Consume all elements from the iterator and produce a result.

        Args:
            iterator: An iterator producing elements to consume

        Returns:
            The result of consuming all elements
        """
        ...

    @abstractmethod
    def split(self) -> tuple[Consumer[T_contra, R], Consumer[T_contra, R]]:
        """
        Split this consumer into two independent consumers.

        Returns:
            A tuple of (left_consumer, right_consumer)
        """
        ...

    @abstractmethod
    def reduce(self, left: R, right: R) -> R:
        """
        Combine results from two consumers.

        Args:
            left: Result from the left consumer
            right: Result from the right consumer

        Returns:
            The combined result
        """
        ...


class Producer(Protocol[T_co]):
    """
    A producer represents a splittable data source that can generate iterators.

    Producers know how to split themselves at specific indices and convert
    to sequential iterators for processing.
    """

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of elements this producer will generate."""
        ...

    @abstractmethod
    def split_at(self, index: int) -> tuple[Producer[T_co], Producer[T_co]]:
        """
        Split this producer at the given index.

        Args:
            index: The split point (0 < index < len(self))

        Returns:
            A tuple of (left_producer, right_producer) where left contains
            elements [0, index) and right contains elements [index, len)
        """
        ...

    @abstractmethod
    def into_iter(self) -> Iterator[T_co]:
        """
        Convert this producer into a sequential iterator.

        Returns:
            An iterator that yields all elements
        """
        ...


class UnindexedProducer(Protocol[T_co]):
    """
    A producer for unindexed parallel iterators where the length is unknown.

    This is used for iterators where we don't know the exact count of elements
    in advance, such as filtered sequences.
    """

    @abstractmethod
    def can_split(self) -> bool:
        """Return True if this producer can be split further."""
        ...

    @abstractmethod
    def split(
        self,
    ) -> tuple[UnindexedProducer[T_co], UnindexedProducer[T_co]] | None:
        """
        Attempt to split this producer.

        Returns:
            A tuple of (left, right) producers if splitting is possible,
            None otherwise
        """
        ...

    @abstractmethod
    def into_iter(self) -> Iterator[T_co]:
        """Convert this producer into a sequential iterator."""
        ...
