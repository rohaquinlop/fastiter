"""
FastIter - Parallel Iterators for Python 3.14+ Free-Threaded Mode

A high-performance parallel iteration library,
designed to take full advantage of Python 3.14's free-threaded execution.
"""

import sys
import warnings

if sys._is_gil_enabled():
    warnings.warn(
        "FastIter is running with the GIL enabled. "
        "CPU-bound parallel operations will likely be SLOWER than sequential "
        "due to thread overhead and GIL contention. "
        "For real speedups, use a free-threaded build: python3.14t "
        '(verify with: python -c "import sys; print(sys._is_gil_enabled())").',
        RuntimeWarning,
        stacklevel=2,
    )

from .adapters import IntoParallelIterator, into_par_iter, par_range
from .config import ThreadPoolConfig, get_num_threads, set_num_threads
from .core import IndexedParallelIterator, ParallelIterator
from .producers import ListProducer, RangeProducer

__version__ = "0.1.0"

__all__ = [
    "ParallelIterator",
    "IndexedParallelIterator",
    "IntoParallelIterator",
    "into_par_iter",
    "par_range",
    "RangeProducer",
    "ListProducer",
    "ThreadPoolConfig",
    "set_num_threads",
    "get_num_threads",
]
