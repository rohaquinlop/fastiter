"""
Configuration for thread pool and parallel execution.

This module manages the global thread pool configuration and provides
settings for controlling parallel execution behavior.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor


class ThreadPoolConfig:
    """
    Global configuration for parallel execution.

    This class manages the thread pool used for parallel iteration and
    provides settings for controlling parallelization behavior.
    """

    _instance: ThreadPoolConfig | None = None
    _lock = threading.Lock()

    def __init__(self):
        self._num_threads: int | None = None
        self._executor: ThreadPoolExecutor | None = None
        # Minimum elements before splitting (increased to reduce overhead)
        self._min_split_size = 10000
        # Maximum recursion depth for splitting (reduced to prevent exhaustion)
        self._max_depth = 8

    @classmethod
    def global_config(cls) -> ThreadPoolConfig:
        """Get the global thread pool configuration instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ThreadPoolConfig()
        return cls._instance

    def get_num_threads(self) -> int:
        """
        Get the number of threads to use for parallel execution.

        Returns:
            Number of threads (defaults to CPU count)
        """
        if self._num_threads is None:
            # Try to get from environment variable
            env_threads = os.environ.get("FASTITER_NUM_THREADS")
            if env_threads:
                try:
                    self._num_threads = int(env_threads)
                except ValueError:
                    pass

            # Default to CPU count
            if self._num_threads is None:
                self._num_threads = os.cpu_count() or 4

        return self._num_threads

    def set_num_threads(self, num_threads: int) -> None:
        """
        Set the number of threads to use for parallel execution.

        Args:
            num_threads: Number of threads (must be >= 1)

        Raises:
            ValueError: If num_threads < 1
        """
        if num_threads < 1:
            raise ValueError("Number of threads must be at least 1")

        with self._lock:
            self._num_threads = num_threads
            if self._executor is not None:
                self._executor.shutdown(wait=False)
                self._executor = None

    def get_executor(self) -> ThreadPoolExecutor:
        """
        Get or create the global thread pool executor.

        Returns:
            The global ThreadPoolExecutor instance
        """
        if self._executor is None:
            with self._lock:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(
                        max_workers=self.get_num_threads(),
                        thread_name_prefix="fastiter",
                    )
        return self._executor

    def shutdown(self) -> None:
        """Shutdown the thread pool executor."""
        with self._lock:
            if self._executor is not None:
                self._executor.shutdown(wait=True)
                self._executor = None

    @property
    def min_split_size(self) -> int:
        """
        Minimum number of elements before splitting work.

        Chunks smaller than this won't be split further, preventing
        excessive overhead from fine-grained parallelism.
        """
        return self._min_split_size

    @min_split_size.setter
    def min_split_size(self, value: int) -> None:
        """Set minimum split size."""
        if value < 1:
            raise ValueError("Minimum split size must be at least 1")
        self._min_split_size = value

    @property
    def max_depth(self) -> int:
        """
        Maximum recursion depth for work splitting.

        This prevents excessive splitting that could lead to stack overflow
        or performance degradation.
        """
        return self._max_depth

    @max_depth.setter
    def max_depth(self, value: int) -> None:
        """Set maximum depth."""
        if value < 1:
            raise ValueError("Maximum depth must be at least 1")
        self._max_depth = value


# Global configuration instance
_global_config = ThreadPoolConfig.global_config()


def set_num_threads(num_threads: int) -> None:
    """
    Set the global number of threads for parallel execution.

    Args:
        num_threads: Number of threads to use

    Example:
        >>> from fastiter import set_num_threads
        >>> set_num_threads(8)
    """
    _global_config.set_num_threads(num_threads)


def get_num_threads() -> int:
    """
    Get the current number of threads for parallel execution.

    Returns:
        Current number of threads
    """
    return _global_config.get_num_threads()
