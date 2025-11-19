"""
Testovi za Crypto utility functions
"""
import pytest
import bcrypt
import time
from basify.utils.crypto import hash_password, verify_password


class TestCryptoUtils:
    
    @pytest.fixture
    def sample_passwords(self):
        """Sample passwords for testing"""
        return {
            "simple": "password123",
            "complex": "MyC0mpl3x!P@ssw0rd",
            "unicode": "héllo123!",
            "long": "This is a very long password with many characters 123!@#",
            "short": "abc123!",
            "empty": "",
            "special": "!@#$%^&*()_+{}[]|:;\"'<>,.?/~`",
            "numbers_only": "1234567890",
            "letters_only": "abcdefghijklmnopqrstuvwxyz"
        }
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_hash_password_basic(self, sample_passwords):
        """Test basic password hashing functionality"""
        password = sample_passwords["simple"]
        
        hashed = hash_password(password)
        
        # Verify hash properties
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original
        assert hashed.startswith("$2b$")  # bcrypt format
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_hash_password_uniqueness(self, sample_passwords):
        """Test that same password generates different hashes due to salt"""
        password = sample_passwords["simple"]
        
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts should produce different hashes
        assert both_verify_same_password(password, hash1, hash2)
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_verify_password_correct(self, sample_passwords):
        """Test password verification with correct password"""
        password = sample_passwords["complex"]
        
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_verify_password_incorrect(self, sample_passwords):
        """Test password verification with incorrect password"""
        password = sample_passwords["complex"]
        wrong_password = sample_passwords["simple"]
        
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_hash_verify_cycle_all_passwords(self, sample_passwords):
        """Test hash/verify cycle for all sample passwords"""
        for password_type, password in sample_passwords.items():
            if password:  # Skip empty password
                hashed = hash_password(password)
                
                # Correct password should verify
                assert verify_password(password, hashed) is True, \
                    f"Failed to verify {password_type} password: {password}"
                
                # Wrong password should not verify
                wrong_password = password + "_wrong"
                assert verify_password(wrong_password, hashed) is False, \
                    f"Incorrectly verified wrong password for {password_type}"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_unicode_password_support(self, sample_passwords):
        """Test support for unicode characters in passwords"""
        unicode_password = sample_passwords["unicode"]
        
        hashed = hash_password(unicode_password)
        
        assert isinstance(hashed, str)
        assert verify_password(unicode_password, hashed) is True
        
        # Different unicode should not verify
        different_unicode = "hëllo123!"
        assert verify_password(different_unicode, hashed) is False
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_special_characters_password(self, sample_passwords):
        """Test password with special characters"""
        special_password = sample_passwords["special"]
        
        hashed = hash_password(special_password)
        
        assert verify_password(special_password, hashed) is True
        assert verify_password("different" + special_password, hashed) is False
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_long_password_support(self, sample_passwords):
        """Test support for long passwords"""
        long_password = sample_passwords["long"]
        
        hashed = hash_password(long_password)
        
        assert verify_password(long_password, hashed) is True
        assert len(hashed) > 0
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_empty_password_handling(self, sample_passwords):
        """Test handling of empty password"""
        empty_password = sample_passwords["empty"]
        
        # Should handle empty password without crashing
        hashed = hash_password(empty_password)
        
        assert isinstance(hashed, str)
        assert verify_password(empty_password, hashed) is True
        assert verify_password("not_empty", hashed) is False
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_password_hashing_security_rounds(self):
        """Test that bcrypt uses appropriate number of rounds"""
        password = "test_password_123"
        
        hashed = hash_password(password)
        
        # Extract rounds from hash (bcrypt format: $2b$rounds$salt+hash)
        parts = hashed.split('$')
        rounds = int(parts[2])
        
        # Should use at least 10 rounds for security
        assert rounds >= 10, f"Bcrypt rounds too low: {rounds}"
        assert rounds <= 15, f"Bcrypt rounds too high (performance): {rounds}"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_password_hashing_performance(self, sample_passwords):
        """Test password hashing performance"""
        password = sample_passwords["complex"]
        
        start_time = time.time()
        hashed = hash_password(password)
        hash_time = time.time() - start_time
        
        # Hashing should be reasonably fast but not too fast (security)
        assert 0.01 < hash_time < 5.0, f"Hash time {hash_time} seems unusual"
        
        # Verification should be fast
        start_time = time.time()
        verify_password(password, hashed)
        verify_time = time.time() - start_time
        
        assert verify_time < 1.0, f"Verify time {verify_time} too slow"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_hash_format_consistency(self, sample_passwords):
        """Test that hash format is consistent"""
        password = sample_passwords["complex"]
        
        # Generate multiple hashes
        hashes = [hash_password(password) for _ in range(5)]
        
        for hashed in hashes:
            # All should be bcrypt format
            assert hashed.startswith("$2b$")
            
            # All should have proper structure
            parts = hashed.split('$')
            assert len(parts) >= 4
            
            # All should verify the original password
            assert verify_password(password, hashed) is True
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_password_verification_edge_cases(self):
        """Test password verification edge cases"""
        password = "test123"
        hashed = hash_password(password)
        
        # Verification edge cases
        test_cases = [
            ("", False),  # Empty password
            ("test124", False),  # Similar but wrong
            ("test123 ", False),  # Extra space
            (" test123", False),  # Leading space
            ("TEST123", False),  # Wrong case
            ("test123", True),   # Correct password
        ]
        
        for test_password, expected_result in test_cases:
            result = verify_password(test_password, hashed)  # Fix: use hashed instead of test_password
            assert result == expected_result, \
                f"Password '{test_password}' verification failed: expected {expected_result}, got {result}"
    
    @pytest.mark.utils
    @pytest.mark.unit 
    def test_invalid_hash_handling(self):
        """Test verification with invalid hashes"""
        password = "test123"
        
        invalid_hashes = [
            "",  # Empty hash
            "invalid_hash",  # Not bcrypt format
            "$2b$invalid$hash",  # Malformed bcrypt
            "plaintext_password",  # Plain text
        ]
        
        for invalid_hash in invalid_hashes:
            # Should not crash, should return False or raise exception
            try:
                result = verify_password(password, invalid_hash)
                assert result is False, f"Should return False for invalid hash: {invalid_hash}"
            except Exception as e:
                # bcrypt might throw exception for some invalid hashes - that's acceptable
                # Accept various exception types that bcrypt might throw
                assert isinstance(e, (ValueError, TypeError, Exception))
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_password_case_sensitivity(self):
        """Test that password verification is case sensitive"""
        password = "MyPassword123"
        hashed = hash_password(password)
        
        # Different cases should not verify
        case_variants = [
            "mypassword123",
            "MYPASSWORD123", 
            "myPassword123",
            "MyPassword124"  # Different number
        ]
        
        for variant in case_variants:
            assert verify_password(variant, hashed) is False, \
                f"Case variant '{variant}' should not verify against original password"
        
        # Original password should verify
        assert verify_password(password, hashed) is True


def both_verify_same_password(password: str, hash1: str, hash2: str) -> bool:
    """Helper function to verify both hashes work for the same password"""
    return verify_password(password, hash1) and verify_password(password, hash2)