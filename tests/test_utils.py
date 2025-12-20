"""Tests for utility functions."""


from cluspro.utils import expand_sequences, format_job_ids, group_sequences


class TestExpandSequences:
    """Tests for expand_sequences function."""

    def test_single_number(self):
        """Test expanding a single number."""
        assert expand_sequences("5") == [5]

    def test_simple_range(self):
        """Test expanding a simple range."""
        assert expand_sequences("1:5") == [1, 2, 3, 4, 5]

    def test_comma_separated(self):
        """Test expanding comma-separated numbers."""
        assert expand_sequences("1,3,5") == [1, 3, 5]

    def test_mixed(self):
        """Test expanding mixed notation."""
        result = expand_sequences("1:3,5,7:9")
        assert result == [1, 2, 3, 5, 7, 8, 9]

    def test_empty_string(self):
        """Test empty string returns empty list."""
        assert expand_sequences("") == []

    def test_whitespace(self):
        """Test handling of whitespace."""
        assert expand_sequences(" 1:3 , 5 ") == [1, 2, 3, 5]

    def test_real_job_ids(self):
        """Test with realistic job IDs."""
        result = expand_sequences("958743:958745,958747:958748,958750")
        assert result == [958743, 958744, 958745, 958747, 958748, 958750]


class TestGroupSequences:
    """Tests for group_sequences function."""

    def test_single_number(self):
        """Test compressing a single number."""
        assert group_sequences([5]) == "5"

    def test_consecutive_range(self):
        """Test compressing consecutive numbers."""
        assert group_sequences([1, 2, 3, 4, 5]) == "1:5"

    def test_non_consecutive(self):
        """Test compressing non-consecutive numbers."""
        assert group_sequences([1, 3, 5]) == "1,3,5"

    def test_mixed(self):
        """Test compressing mixed sequences."""
        result = group_sequences([1, 2, 3, 5, 7, 8, 9])
        assert result == "1:3,5,7:9"

    def test_empty_list(self):
        """Test empty list returns empty string."""
        assert group_sequences([]) == ""

    def test_unsorted_input(self):
        """Test that unsorted input is handled."""
        result = group_sequences([5, 1, 3, 2, 4])
        assert result == "1:5"

    def test_duplicates(self):
        """Test that duplicates are handled."""
        result = group_sequences([1, 2, 2, 3, 3, 3])
        assert result == "1:3"

    def test_real_job_ids(self):
        """Test with realistic job IDs."""
        result = group_sequences([958743, 958745, 958744, 958748, 958747, 958750])
        assert result == "958743:958745,958747:958748,958750"


class TestRoundTrip:
    """Test that expand and group are inverses."""

    def test_roundtrip_simple(self):
        """Test roundtrip for simple sequence."""
        original = "1:5,7,9:11"
        expanded = expand_sequences(original)
        compressed = group_sequences(expanded)
        assert compressed == original

    def test_roundtrip_complex(self):
        """Test roundtrip for complex sequence."""
        original = "958743:958745,958747:958748,958750,958752"
        expanded = expand_sequences(original)
        compressed = group_sequences(expanded)
        assert compressed == original


class TestFormatJobIds:
    """Tests for format_job_ids function."""

    def test_default_items_per_line(self):
        """Test default formatting."""
        result = format_job_ids("1,2,3,4,5,6,7,8", items_per_line=3)
        lines = result.split(",\n")
        assert len(lines) == 3
        assert lines[0] == "1,2,3"
        assert lines[1] == "4,5,6"
        assert lines[2] == "7,8"

    def test_fewer_items_than_limit(self):
        """Test with fewer items than limit."""
        result = format_job_ids("1,2,3", items_per_line=5)
        assert result == "1,2,3"
