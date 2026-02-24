"""
Property-based tests for parallel iterator operations.

Uses hypothesis to verify that parallel results always match sequential results
for map, filter, reduce, sum, flat_map, and zip.  Module-level worker functions
are required for free-threaded CPython (3.14t): closures serialise on shared
cell state, eliminating parallelism and making correctness harder to observe.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from fastiter import into_par_iter, par_range

# ---------------------------------------------------------------------------
# Module-level worker functions (required for correct free-threaded scaling)
# ---------------------------------------------------------------------------


def _double(x: int) -> int:
    return x * 2


def _square(x: int) -> int:
    return x * x


def _is_even(x: int) -> bool:
    return x % 2 == 0


def _is_positive(x: int) -> bool:
    return x > 0


def _add(a: int, b: int) -> int:
    return a + b


def _zero() -> int:
    return 0


def _repeat_twice(x: int) -> list[int]:
    return [x, x]


def _range_to_n(x: int) -> range:
    return range(abs(x) % 5)


# ---------------------------------------------------------------------------
# map
# ---------------------------------------------------------------------------


@given(st.lists(st.integers(min_value=-1000, max_value=1000), max_size=500))
@settings(max_examples=100)
def test_map_double_matches_sequential(lst: list[int]) -> None:
    parallel = sorted(into_par_iter(lst).map(_double).collect())
    sequential = sorted(x * 2 for x in lst)
    assert parallel == sequential


@given(st.integers(min_value=0, max_value=2000))
@settings(max_examples=50)
def test_map_square_on_range(n: int) -> None:
    parallel = sorted(par_range(0, n).map(_square).collect())
    sequential = sorted(x * x for x in range(n))
    assert parallel == sequential


# ---------------------------------------------------------------------------
# filter
# ---------------------------------------------------------------------------


@given(st.lists(st.integers(min_value=-1000, max_value=1000), max_size=500))
@settings(max_examples=100)
def test_filter_even_matches_sequential(lst: list[int]) -> None:
    parallel = sorted(into_par_iter(lst).filter(_is_even).collect())
    sequential = sorted(x for x in lst if x % 2 == 0)
    assert parallel == sequential


@given(st.integers(min_value=0, max_value=2000))
@settings(max_examples=50)
def test_filter_even_on_range(n: int) -> None:
    parallel = sorted(par_range(0, n).filter(_is_even).collect())
    sequential = sorted(x for x in range(n) if x % 2 == 0)
    assert parallel == sequential


# ---------------------------------------------------------------------------
# sum
# ---------------------------------------------------------------------------


@given(st.lists(st.integers(min_value=-10000, max_value=10000), max_size=500))
@settings(max_examples=100)
def test_sum_matches_sequential(lst: list[int]) -> None:
    assert into_par_iter(lst).sum() == sum(lst)


@given(st.integers(min_value=0, max_value=5000))
@settings(max_examples=50)
def test_sum_range_matches_sequential(n: int) -> None:
    assert par_range(0, n).sum() == sum(range(n))


# ---------------------------------------------------------------------------
# reduce
# ---------------------------------------------------------------------------


@given(st.lists(st.integers(min_value=-1000, max_value=1000), max_size=500))
@settings(max_examples=100)
def test_reduce_add_matches_sum(lst: list[int]) -> None:
    parallel = into_par_iter(lst).reduce(_zero, _add)
    assert parallel == sum(lst)


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


@given(st.integers(min_value=0, max_value=3000))
@settings(max_examples=50)
def test_count_range(n: int) -> None:
    assert par_range(0, n).count() == n


@given(st.lists(st.integers(min_value=-100, max_value=100), max_size=500))
@settings(max_examples=100)
def test_filter_count_matches_sequential(lst: list[int]) -> None:
    parallel = into_par_iter(lst).filter(_is_positive).count()
    sequential = sum(1 for x in lst if x > 0)
    assert parallel == sequential


# ---------------------------------------------------------------------------
# flat_map
# ---------------------------------------------------------------------------


@given(st.lists(st.integers(min_value=0, max_value=20), max_size=200))
@settings(max_examples=100)
def test_flat_map_repeat_matches_sequential(lst: list[int]) -> None:
    parallel = sorted(into_par_iter(lst).flat_map(_repeat_twice).collect())
    sequential = sorted(x for item in lst for x in [item, item])
    assert parallel == sequential


@given(st.lists(st.integers(min_value=0, max_value=10), max_size=200))
@settings(max_examples=100)
def test_flat_map_range_matches_sequential(lst: list[int]) -> None:
    parallel = sorted(into_par_iter(lst).flat_map(_range_to_n).collect())
    sequential = sorted(x for item in lst for x in range(item % 5))
    assert parallel == sequential


# ---------------------------------------------------------------------------
# zip
# ---------------------------------------------------------------------------


@given(
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=50)
def test_zip_two_ranges_matches_builtin(n: int, m: int) -> None:
    left = par_range(0, n)
    right = list(range(m))
    parallel = sorted(left.zip(right).collect())
    sequential = sorted(zip(range(n), range(m), strict=False))
    assert parallel == sequential


@given(
    st.lists(st.integers(min_value=-100, max_value=100), max_size=300),
    st.lists(st.integers(min_value=-100, max_value=100), max_size=300),
)
@settings(max_examples=100)
def test_zip_two_lists_matches_builtin(a: list[int], b: list[int]) -> None:
    parallel = sorted(into_par_iter(a).zip(b).collect())
    sequential = sorted(zip(a, b, strict=False))
    assert parallel == sequential
