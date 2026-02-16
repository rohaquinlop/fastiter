"""
Producer implementations for common data structures.

Producers convert data structures into splittable iterators that can be
processed in parallel.
"""

from collections.abc import Iterator, Sequence
from typing import TypeVar

from .protocols import Producer

T = TypeVar("T")


class RangeProducer:
    """
    Producer for range objects.

    This efficiently splits numeric ranges for parallel processing.
    """

    def __init__(self, start: int, stop: int, step: int = 1):
        """
        Create a range producer.

        Args:
            start: Starting value (inclusive)
            stop: Ending value (exclusive)
            step: Step size (default 1)
        """
        if step == 0:
            raise ValueError("Range step cannot be zero")

        self.start = start
        self.stop = stop
        self.step = step

        # Calculate actual length
        if step > 0:
            self._length = max(0, (stop - start + step - 1) // step)
        else:
            self._length = max(0, (stop - start + step + 1) // step)

    def __len__(self) -> int:
        """Return the number of elements in this range."""
        return self._length

    def split_at(self, index: int) -> tuple[RangeProducer, RangeProducer]:
        """
        Split this range at the given index.

        Args:
            index: Split position (0 < index < len(self))

        Returns:
            Tuple of (left_range, right_range)
        """
        if index <= 0 or index >= self._length:
            raise ValueError(f"Invalid split index: {index}")

        # Calculate the actual value at the split point
        mid_value = self.start + (index * self.step)

        left = RangeProducer(self.start, mid_value, self.step)
        right = RangeProducer(mid_value, self.stop, self.step)

        return left, right

    def into_iter(self) -> Iterator[int]:
        """Convert this range into an iterator."""
        return iter(range(self.start, self.stop, self.step))


class ListProducer(Producer[T]):
    """
    Producer for list-like sequences.

    This wraps lists, tuples, and other sequences for parallel processing.
    """

    def __init__(
        self, data: Sequence[T], start: int = 0, end: int | None = None
    ):
        """
        Create a list producer.

        Args:
            data: The sequence to iterate over
            start: Starting index (inclusive)
            end: Ending index (exclusive), or None for end of sequence
        """
        self.data = data
        self.start = start
        self.end = end if end is not None else len(data)

        if self.start < 0 or self.start > len(data):
            raise ValueError(f"Invalid start index: {self.start}")
        if self.end < 0 or self.end > len(data):
            raise ValueError(f"Invalid end index: {self.end}")
        if self.start > self.end:
            raise ValueError(f"Start index {self.start} > end index {self.end}")

    def __len__(self) -> int:
        """Return the number of elements in this slice."""
        return self.end - self.start

    def split_at(self, index: int) -> tuple[ListProducer[T], ListProducer[T]]:
        """
        Split this sequence at the given index.

        Args:
            index: Split position relative to start (0 < index < len(self))

        Returns:
            Tuple of (left_producer, right_producer)
        """
        length = self.end - self.start
        if index <= 0 or index >= length:
            raise ValueError(f"Invalid split index: {index}")

        mid = self.start + index

        left = ListProducer(self.data, self.start, mid)
        right = ListProducer(self.data, mid, self.end)

        return left, right

    def into_iter(self) -> Iterator[T]:
        """Convert this sequence slice into an iterator."""
        return iter(self.data[self.start : self.end])


class TupleProducer(Producer[T]):
    """
    Producer for tuples.

    Similar to ListProducer but optimized for tuples.
    """

    def __init__(
        self, data: tuple[T, ...], start: int = 0, end: int | None = None
    ):
        """
        Create a tuple producer.

        Args:
            data: The tuple to iterate over
            start: Starting index (inclusive)
            end: Ending index (exclusive), or None for end of tuple
        """
        self.data = data
        self.start = start
        self.end = end if end is not None else len(data)

    def __len__(self) -> int:
        """Return the number of elements in this slice."""
        return self.end - self.start

    def split_at(self, index: int) -> tuple[TupleProducer[T], TupleProducer[T]]:
        """Split this tuple at the given index."""
        length = self.end - self.start
        if index <= 0 or index >= length:
            raise ValueError(f"Invalid split index: {index}")

        mid = self.start + index

        left = TupleProducer(self.data, self.start, mid)
        right = TupleProducer(self.data, mid, self.end)

        return left, right

    def into_iter(self) -> Iterator[T]:
        """Convert this tuple slice into an iterator."""
        return iter(self.data[self.start : self.end])


class ChainProducer(Producer[T]):
    """
    Producer that chains multiple producers together.

    This allows combining multiple data sources into a single parallel iterator.
    """

    def __init__(self, producers: list[Producer[T]]):
        """
        Create a chain producer.

        Args:
            producers: List of producers to chain together
        """
        self.producers = producers
        self._length = sum(len(p) for p in producers)

    def __len__(self) -> int:
        """Return total number of elements across all producers."""
        return self._length

    def split_at(self, index: int) -> tuple[ChainProducer[T], ChainProducer[T]]:
        """
        Split the chain at the given index.

        This finds which producer contains the split point and splits there.
        """
        if index <= 0 or index >= self._length:
            raise ValueError(f"Invalid split index: {index}")

        cumulative = 0
        for i, producer in enumerate(self.producers):
            producer_len = len(producer)
            if cumulative + producer_len > index:
                # Split point is within this producer
                local_index = index - cumulative

                if local_index == 0:
                    # Split between producers
                    left = ChainProducer(self.producers[:i])
                    right = ChainProducer(self.producers[i:])
                else:
                    # Split within this producer
                    left_prod, right_prod = producer.split_at(local_index)
                    left = ChainProducer(self.producers[:i] + [left_prod])
                    right = ChainProducer(
                        [right_prod] + self.producers[i + 1 :]
                    )

                return left, right

            cumulative += producer_len

        raise RuntimeError("Split index calculation error")

    def into_iter(self) -> Iterator[T]:
        """Chain all producers into a single iterator."""
        for producer in self.producers:
            yield from producer.into_iter()
