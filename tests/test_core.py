"""
Tests for core parallel iterator functionality.
"""

from fastiter import into_par_iter, par_range, set_num_threads


class TestParallelRange:
    """Tests for parallel range iterator."""

    def test_sum(self):
        """Test sum operation."""
        result = par_range(0, 100).sum()
        expected = sum(range(100))
        assert result == expected

    def test_map(self):
        """Test map operation."""
        result = par_range(0, 10).map(lambda x: x * 2).collect()
        expected = [x * 2 for x in range(10)]
        assert sorted(result) == sorted(expected)

    def test_filter(self):
        """Test filter operation."""
        result = par_range(0, 20).filter(lambda x: x % 2 == 0).collect()
        expected = [x for x in range(20) if x % 2 == 0]
        assert sorted(result) == sorted(expected)

    def test_map_sum(self):
        """Test chained map and sum."""
        result = par_range(0, 100).map(lambda x: x * x).sum()
        expected = sum(x * x for x in range(100))
        assert result == expected

    def test_filter_sum(self):
        """Test chained filter and sum."""
        result = par_range(0, 100).filter(lambda x: x % 3 == 0).sum()
        expected = sum(x for x in range(100) if x % 3 == 0)
        assert result == expected

    def test_count(self):
        """Test count operation."""
        result = par_range(0, 1000).count()
        assert result == 1000

    def test_filter_count(self):
        """Test filter and count."""
        result = par_range(0, 100).filter(lambda x: x % 5 == 0).count()
        expected = len([x for x in range(100) if x % 5 == 0])
        assert result == expected

    def test_empty_range(self):
        """Test empty range."""
        result = par_range(0, 0).sum()
        assert result == 0

        result = par_range(0, 0).count()
        assert result == 0

    def test_single_element(self):
        """Test single element range."""
        result = par_range(5, 6).collect()
        assert result == [5]


class TestParallelList:
    """Tests for parallel list iterator."""

    def test_list_sum(self):
        """Test sum on list."""
        data = list(range(100))
        result = into_par_iter(data).sum()
        expected = sum(data)
        assert result == expected

    def test_list_map(self):
        """Test map on list."""
        data = [1, 2, 3, 4, 5]
        result = into_par_iter(data).map(lambda x: x * 2).collect()
        expected = [x * 2 for x in data]
        assert sorted(result) == sorted(expected)

    def test_tuple(self):
        """Test with tuple."""
        data = (1, 2, 3, 4, 5)
        result = into_par_iter(data).sum()
        expected = sum(data)
        assert result == expected

    def test_empty_list(self):
        """Test empty list."""
        result = into_par_iter([]).sum()
        assert result == 0

    def test_strings(self):
        """Test with strings."""
        words = ["hello", "world", "test"]
        result = into_par_iter(words).map(len).collect()
        expected = [len(w) for w in words]
        assert sorted(result) == sorted(expected)


class TestComplexPipelines:
    """Tests for complex iterator pipelines."""

    def test_multi_map(self):
        """Test multiple map operations."""
        result = (
            par_range(0, 10)
            .map(lambda x: x + 1)
            .map(lambda x: x * 2)
            .map(lambda x: x - 1)
            .collect()
        )
        expected = [(x + 1) * 2 - 1 for x in range(10)]
        assert sorted(result) == sorted(expected)

    def test_multi_filter(self):
        """Test multiple filter operations."""
        result = (
            par_range(0, 100)
            .filter(lambda x: x % 2 == 0)
            .filter(lambda x: x % 3 == 0)
            .collect()
        )
        expected = [x for x in range(100) if x % 2 == 0 and x % 3 == 0]
        assert sorted(result) == sorted(expected)

    def test_map_filter_map(self):
        """Test alternating map and filter."""
        result = (
            par_range(0, 50)
            .map(lambda x: x * 2)
            .filter(lambda x: x > 20)
            .map(lambda x: x + 1)
            .collect()
        )
        expected = [(x * 2) + 1 for x in range(50) if (x * 2) > 20]
        assert sorted(result) == sorted(expected)

    def test_long_pipeline(self):
        """Test a long pipeline."""
        result = (
            par_range(0, 100)
            .map(lambda x: x + 1)
            .filter(lambda x: x % 2 == 0)
            .map(lambda x: x * 2)
            .filter(lambda x: x < 100)
            .map(lambda x: x - 1)
            .sum()
        )

        expected = sum(
            ((x + 1) * 2) - 1
            for x in range(100)
            if (x + 1) % 2 == 0 and (x + 1) * 2 < 100
        )
        assert result == expected


class TestReduction:
    """Tests for reduction operations."""

    def test_custom_reduce(self):
        """Test custom reduce operation."""
        result = par_range(1, 11).reduce(lambda: 1, lambda a, b: a * b)
        expected = 1
        for i in range(1, 11):
            expected *= i
        assert result == expected

    def test_reduce_with_identity(self):
        """Test that identity is used correctly."""
        result = par_range(1, 5).reduce(lambda: 0, lambda a, b: a + b)
        expected = sum(range(1, 5))
        assert result == expected

    def test_sum_equivalence(self):
        """Test that reduce matches sum."""
        data = list(range(100))
        result1 = into_par_iter(data).sum()
        result2 = into_par_iter(data).reduce(lambda: 0, lambda a, b: a + b)
        assert result1 == result2


class TestMinMax:
    """Tests for min and max operations."""

    def test_min(self):
        """Test min operation."""
        result = par_range(10, 100).min()
        assert result == 10

    def test_max(self):
        """Test max operation."""
        result = par_range(10, 100).max()
        assert result == 99

    def test_min_with_key(self):
        """Test min with key function."""
        words = ["a", "abc", "ab", "abcde"]
        result = into_par_iter(words).min(key=len)
        assert result == "a"

    def test_max_with_key(self):
        """Test max with key function."""
        words = ["a", "abc", "ab", "abcde"]
        result = into_par_iter(words).max(key=len)
        assert result == "abcde"

    def test_empty_min(self):
        """Test min on empty iterator."""
        result = par_range(0, 0).min()
        assert result is None

    def test_empty_max(self):
        """Test max on empty iterator."""
        result = par_range(0, 0).max()
        assert result is None


class TestAnyAll:
    """Tests for any and all operations."""

    def test_any_true(self):
        """Test any when condition is true."""
        result = par_range(0, 10).any(lambda x: x == 5)
        assert result is True

    def test_any_false(self):
        """Test any when condition is false."""
        result = par_range(0, 10).any(lambda x: x > 100)
        assert result is False

    def test_all_true(self):
        """Test all when condition is true."""
        result = par_range(0, 10).all(lambda x: x < 100)
        assert result is True

    def test_all_false(self):
        """Test all when condition is false."""
        result = par_range(0, 10).all(lambda x: x < 5)
        assert result is False

    def test_any_default_predicate(self):
        """Test any with default predicate."""
        result = into_par_iter([0, 0, 1, 0]).any()
        assert result is True

    def test_all_default_predicate(self):
        """Test all with default predicate."""
        result = into_par_iter([1, 2, 3, 4]).all()
        assert result is True


class TestThreadConfiguration:
    """Tests for thread configuration."""

    def test_set_num_threads(self):
        """Test setting number of threads."""
        set_num_threads(4)
        result = par_range(0, 100).sum()
        expected = sum(range(100))
        assert result == expected

    def test_single_thread(self):
        """Test with single thread."""
        set_num_threads(1)
        result = par_range(0, 100).map(lambda x: x * 2).sum()
        expected = sum(x * 2 for x in range(100))
        assert result == expected

        # Reset to default
        set_num_threads(4)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_large_numbers(self):
        """Test with large numbers."""
        result = par_range(0, 1000).map(lambda x: x ** 2).sum()
        expected = sum(x ** 2 for x in range(1000))
        assert result == expected

    def test_negative_numbers(self):
        """Test with negative numbers."""
        data = list(range(-50, 50))
        result = into_par_iter(data).sum()
        expected = sum(data)
        assert result == expected

    def test_floating_point(self):
        """Test with floating point."""
        data = [1.5, 2.5, 3.5, 4.5]
        result = into_par_iter(data).sum()
        expected = sum(data)
        assert abs(result - expected) < 1e-10

    def test_filter_all_out(self):
        """Test filter that removes all elements."""
        result = par_range(0, 10).filter(lambda x: x > 100).collect()
        assert result == []

    def test_filter_none_out(self):
        """Test filter that keeps all elements."""
        result = par_range(0, 10).filter(lambda x: x >= 0).collect()
        expected = list(range(10))
        assert sorted(result) == sorted(expected)
