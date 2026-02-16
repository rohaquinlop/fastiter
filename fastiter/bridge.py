"""
Bridge functions that connect producers and consumers.

The bridge implements the divide-and-conquer strategy, splitting work
across threads and combining results.
"""

from concurrent.futures import Future
from typing import TypeVar

from .config import ThreadPoolConfig
from .protocols import Consumer, Producer, UnindexedProducer

T = TypeVar("T")
R = TypeVar("R")


def bridge(
    producer: Producer[T], consumer: Consumer[T, R], depth: int = 0
) -> R:
    """
    Bridge an indexed producer with a consumer, executing in parallel.

    This implements the core divide-and-conquer algorithm:
    1. If the work is small enough or we're too deep, execute sequentially
    2. Otherwise, split the producer and consumer in half
    3. Execute both halves in parallel
    4. Combine the results

    Args:
        producer: The producer generating elements
        consumer: The consumer processing elements
        depth: Current recursion depth (for preventing excessive splitting)

    Returns:
        The result from the consumer
    """
    config = ThreadPoolConfig.global_config()
    length = len(producer)

    # Base case: execute sequentially if work is small or we're too deep
    if length <= config.min_split_size or depth >= config.max_depth:
        iterator = producer.into_iter()
        return consumer.consume_iter(iterator)

    # Recursive case: split and execute in parallel
    mid = length // 2
    if mid == 0:
        # Can't split further
        iterator = producer.into_iter()
        return consumer.consume_iter(iterator)

    # Split producer and consumer
    left_producer, right_producer = producer.split_at(mid)
    left_consumer, right_consumer = consumer.split()

    num_threads = config.get_num_threads()
    import math

    max_parallel_depth = max(2, min(4, int(math.log2(num_threads)) + 1))

    if depth < max_parallel_depth and num_threads > 1:
        executor = config.get_executor()

        left_future: Future[R] = executor.submit(
            bridge, left_producer, left_consumer, depth + 1
        )

        right_result = bridge(right_producer, right_consumer, depth + 1)

        left_result = left_future.result()
    else:
        left_result = bridge(left_producer, left_consumer, depth + 1)
        right_result = bridge(right_producer, right_consumer, depth + 1)

    return consumer.reduce(left_result, right_result)


def bridge_unindexed(
    producer: UnindexedProducer[T], consumer: Consumer[T, R], depth: int = 0
) -> R:
    """
    Bridge an unindexed producer with a consumer, executing in parallel.

    This is similar to bridge() but works with producers that don't have
    a known length or indexing.

    Args:
        producer: The unindexed producer generating elements
        consumer: The consumer processing elements
        depth: Current recursion depth

    Returns:
        The result from the consumer
    """
    config = ThreadPoolConfig.global_config()

    # Base case: execute sequentially if we can't or shouldn't split
    if not producer.can_split() or depth >= config.max_depth:
        iterator = producer.into_iter()
        return consumer.consume_iter(iterator)

    # Try to split
    split_result = producer.split()
    if split_result is None:
        # Split failed, execute sequentially
        iterator = producer.into_iter()
        return consumer.consume_iter(iterator)

    left_producer, right_producer = split_result
    left_consumer, right_consumer = consumer.split()

    # Execute both halves in parallel
    executor = config.get_executor()

    left_future: Future[R] = executor.submit(
        bridge_unindexed, left_producer, left_consumer, depth + 1
    )

    right_result = bridge_unindexed(right_producer, right_consumer, depth + 1)
    left_result = left_future.result()

    return consumer.reduce(left_result, right_result)


def sequential_bridge(producer: Producer[T], consumer: Consumer[T, R]) -> R:
    """
    Bridge a producer and consumer sequentially (no parallelism).

    This is useful for debugging or when you want to disable parallelism.

    Args:
        producer: The producer generating elements
        consumer: The consumer processing elements

    Returns:
        The result from the consumer
    """
    iterator = producer.into_iter()
    return consumer.consume_iter(iterator)
