"""
Testovi za Helper utility functions
"""
import pytest
import uuid
import re
from datetime import datetime, timezone
from basify.utils.helpers import generate_uuid, current_timestamp, slugify


class TestHelpers:
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_generate_uuid_format(self):
        """Test UUID generation format"""
        generated_uuid = generate_uuid()
        
        # Should be string
        assert isinstance(generated_uuid, str)
        
        # Should be valid UUID format
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, generated_uuid), f"Generated UUID '{generated_uuid}' doesn't match expected format"
        
        # Should be parseable as UUID
        parsed_uuid = uuid.UUID(generated_uuid)
        assert str(parsed_uuid) == generated_uuid
        
        # Should be version 4 UUID
        assert parsed_uuid.version == 4
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_generate_uuid_uniqueness(self):
        """Test that generated UUIDs are unique"""
        uuids = [generate_uuid() for _ in range(100)]
        
        # All should be unique
        unique_uuids = set(uuids)
        assert len(unique_uuids) == len(uuids), "Generated UUIDs are not unique"
        
        # All should be different
        for i in range(len(uuids)):
            for j in range(i + 1, len(uuids)):
                assert uuids[i] != uuids[j], f"UUIDs at positions {i} and {j} are identical: {uuids[i]}"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_current_timestamp_type(self):
        """Test current timestamp returns correct type"""
        timestamp = current_timestamp()
        
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None
        assert timestamp.tzinfo == timezone.utc
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_current_timestamp_recent(self):
        """Test that current timestamp is recent"""
        before = datetime.now(timezone.utc)
        timestamp = current_timestamp()
        after = datetime.now(timezone.utc)
        
        # Should be between before and after
        assert before <= timestamp <= after
        
        # Should be very recent (within 1 second)
        time_diff = (after - timestamp).total_seconds()
        assert time_diff < 1.0, f"Timestamp seems too old: {time_diff} seconds"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_current_timestamp_multiple_calls(self):
        """Test multiple calls to current_timestamp"""
        timestamps = [current_timestamp() for _ in range(5)]
        
        # All should be datetime objects
        for ts in timestamps:
            assert isinstance(ts, datetime)
            assert ts.tzinfo == timezone.utc
        
        # Should be in non-decreasing order (accounting for same millisecond)
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1]
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_basic(self):
        """Test basic slugify functionality"""
        test_cases = [
            ("Hello World", "hello-world"),
            ("Test String", "test-string"),
            ("Simple Text", "simple-text"),
            ("one word", "one-word"),
            ("UPPERCASE", "uppercase"),
            ("MixedCase", "mixedcase"),
        ]
        
        for input_text, expected in test_cases:
            result = slugify(input_text)
            assert result == expected, f"slugify('{input_text}') = '{result}', expected '{expected}'"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_special_characters(self):
        """Test slugify with special characters"""
        test_cases = [
            ("Hello, World!", "hello-world"),
            ("Test & String", "test-string"),
            ("Multi  Spaces", "multi-spaces"),
            ("Remove@Special#Chars", "removespecialchars"),
            ("Keep-Hyphens", "keep-hyphens"),
            ("dots.and.commas,here", "dotsandcommashere"),
            ("numbers123work", "numbers123work"),
            ("trailing spaces   ", "trailing-spaces"),
            ("   leading spaces", "leading-spaces"),
        ]
        
        for input_text, expected in test_cases:
            result = slugify(input_text)
            assert result == expected, f"slugify('{input_text}') = '{result}', expected '{expected}'"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_edge_cases(self):
        """Test slugify edge cases"""
        test_cases = [
            ("", ""),  # Empty string
            ("   ", ""),  # Only spaces
            ("---", ""),  # Only hyphens
            ("   ---   ", ""),  # Spaces and hyphens
            ("!@#$%", ""),  # Only special characters
            ("123", "123"),  # Only numbers
            ("a", "a"),  # Single character
            ("-", ""),  # Single hyphen
            ("--", ""),  # Double hyphen
            ("a-b", "a-b"),  # Single hyphen between chars
            ("a--b", "a-b"),  # Double hyphen should become single
            ("-a-", "a"),  # Leading and trailing hyphens removed
        ]
        
        for input_text, expected in test_cases:
            result = slugify(input_text)
            assert result == expected, f"slugify('{input_text}') = '{result}', expected '{expected}'"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_unicode_characters(self):
        """Test slugify with unicode characters"""
        test_cases = [
            ("Café Restaurant", "caf-restaurant"),
            ("Naïve Approach", "nave-approach"),
            ("Résumé Template", "rsum-template"),
            ("Привет Мир", ""),  # Cyrillic removed
            ("日本語", ""),  # Japanese removed
            ("Mixed English 中文", "mixed-english"),
        ]
        
        for input_text, expected in test_cases:
            result = slugify(input_text)
            assert result == expected, f"slugify('{input_text}') = '{result}', expected '{expected}'"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_multiple_spaces_and_hyphens(self):
        """Test slugify handling of multiple consecutive spaces and hyphens"""
        test_cases = [
            ("multiple    spaces", "multiple-spaces"),
            ("many       spaces    here", "many-spaces-here"),
            ("hyphen-and   space", "hyphen-and-space"),
            ("multiple---hyphens", "multiple-hyphens"),
            ("mixed-  -  -spaces", "mixed-spaces"),
            ("   start and end   ", "start-and-end"),
        ]
        
        for input_text, expected in test_cases:
            result = slugify(input_text)
            assert result == expected, f"slugify('{input_text}') = '{result}', expected '{expected}'"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_preserves_numbers_and_letters(self):
        """Test that slugify preserves alphanumeric characters"""
        test_cases = [
            ("Product 123", "product-123"),
            ("Version 2.0 Release", "version-20-release"),
            ("API v1.2.3", "api-v123"),
            ("Test_123_Case", "test123case"),
            ("file-name-v2", "file-name-v2"),
        ]
        
        for input_text, expected in test_cases:
            result = slugify(input_text)
            assert result == expected, f"slugify('{input_text}') = '{result}', expected '{expected}'"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_long_strings(self):
        """Test slugify with long strings"""
        long_text = "This is a very long string with many words and spaces that should be properly converted to a slug format"
        expected = "this-is-a-very-long-string-with-many-words-and-spaces-that-should-be-properly-converted-to-a-slug-format"
        
        result = slugify(long_text)
        assert result == expected
        
        # Should not have consecutive hyphens
        assert "--" not in result
        
        # Should not start or end with hyphen
        assert not result.startswith("-")
        assert not result.endswith("-")
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_slugify_return_type(self):
        """Test that slugify returns string type"""
        inputs = ["test", "", "123", "Special!@#", "   spaces   "]
        
        for input_text in inputs:
            result = slugify(input_text)
            assert isinstance(result, str), f"slugify should return string, got {type(result)} for input '{input_text}'"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_uuid_timestamp_integration(self):
        """Test using UUID and timestamp together"""
        # Generate unique identifier with timestamp
        timestamp = current_timestamp()
        unique_id = generate_uuid()
        
        # Should be able to create unique combinations
        combinations = []
        for _ in range(10):
            ts = current_timestamp()
            uid = generate_uuid()
            combination = f"{ts.isoformat()}_{uid}"
            combinations.append(combination)
        
        # All combinations should be unique
        assert len(set(combinations)) == len(combinations)
        
        # All should contain valid parts
        for combo in combinations:
            parts = combo.split('_')
            assert len(parts) == 2
            
            # First part should be valid timestamp
            datetime.fromisoformat(parts[0])
            
            # Second part should be valid UUID
            uuid.UUID(parts[1])
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_helpers_no_side_effects(self):
        """Test that helper functions don't have side effects"""
        # Multiple calls should not affect each other
        uuid1 = generate_uuid()
        timestamp1 = current_timestamp()
        slug1 = slugify("Test String")
        
        uuid2 = generate_uuid()
        timestamp2 = current_timestamp()
        slug2 = slugify("Test String")
        
        # UUIDs should be different
        assert uuid1 != uuid2
        
        # Timestamps should be same or later
        assert timestamp1 <= timestamp2
        
        # Same input should produce same slug
        assert slug1 == slug2
        
        # Original calls should still be valid
        assert uuid.UUID(uuid1)  # Should not throw
        assert isinstance(timestamp1, datetime)
        assert isinstance(slug1, str)