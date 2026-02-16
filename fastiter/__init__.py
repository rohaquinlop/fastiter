"""
FastIter - Parallel Iterators for Python 3.14+ Free-Threaded Mode

A high-performance parallel iteration library inspired by Rust's Rayon,
designed to take full advantage of Python 3.14's free-threaded execution.
"""

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
