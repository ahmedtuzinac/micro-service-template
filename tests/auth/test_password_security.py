"""
Testovi za Password Security funkcionalnosti
"""
import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services/auth-service'))

from auth.password import hash_password, verify_password, validate_password_strength
from basify.utils.crypto import hash_password as basify_hash, verify_password as basify_verify


class TestPasswordSecurity:
    
    @pytest.fixture
    def sample_passwords(self):
        """Sample passwords za testiranje"""
        return {
            "weak": "123",
            "medium": "Password123",
            "strong": "MyStr0ngP@ssw0rd!",
            "long": "ThisIsAVeryLongPasswordWithNumbersAnd123!@#",
            "unicode": "Šifra123!@#",
            "empty": "",
            "whitespace": "   ",
            "only_numbers": "12345678",
            "only_letters": "abcdefgh",
            "only_uppercase": "ABCDEFGH",
            "only_lowercase": "abcdefgh",
            "no_special": "Password123",
            "valid_min": "Abcd123!",  # Minimum valid password
        }
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_hash_password_auth_service(self, sample_passwords):
        """Test auth-service password hashing"""
        password = sample_passwords["strong"]
        
        hashed = hash_password(password)
        
        # Verify hash is generated
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original
        
        # Verify bcrypt format (starts with $2b$)
        assert hashed.startswith("$2b$")
        
        # Verify multiple hashes are different
        hashed2 = hash_password(password)
        assert hashed != hashed2  # Salt makes each hash unique
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_verify_password_auth_service(self, sample_passwords):
        """Test auth-service password verification"""
        password = sample_passwords["strong"]
        
        hashed = hash_password(password)
        
        # Correct password should verify
        assert verify_password(password, hashed) is True
        
        # Wrong password should not verify
        assert verify_password("wrong_password", hashed) is False
        assert verify_password(sample_passwords["weak"], hashed) is False
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_hash_password_basify_utils(self, sample_passwords):
        """Test basify utils password hashing"""
        password = sample_passwords["strong"]
        
        hashed = basify_hash(password)
        
        # Verify hash is generated
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password
        
        # Verify bcrypt format
        assert hashed.startswith("$2b$")
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_verify_password_basify_utils(self, sample_passwords):
        """Test basify utils password verification"""
        password = sample_passwords["strong"]
        
        hashed = basify_hash(password)
        
        assert basify_verify(password, hashed) is True
        assert basify_verify("wrong_password", hashed) is False
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_cross_compatibility_auth_basify(self, sample_passwords):
        """Test compatibility between auth-service and basify password functions"""
        password = sample_passwords["strong"]
        
        # Hash with auth-service, verify with basify
        auth_hash = hash_password(password)
        assert basify_verify(password, auth_hash) is True
        
        # Hash with basify, verify with auth-service
        basify_hash_result = basify_hash(password)
        assert verify_password(password, basify_hash_result) is True
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_validate_password_strength_valid(self, sample_passwords):
        """Test password strength validation for valid passwords"""
        valid_passwords = [
            sample_passwords["strong"],
            sample_passwords["valid_min"],
            "Abcd123!",
            "MyP@ssw0rd123",
            "Test123!@#"
        ]
        
        for password in valid_passwords:
            is_valid, error = validate_password_strength(password)
            assert is_valid is True, f"Password '{password}' should be valid but got error: {error}"
            assert error == "", f"Valid password should have no error message, got: {error}"
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_validate_password_strength_too_short(self, sample_passwords):
        """Test password strength validation for too short passwords"""
        short_passwords = [
            sample_passwords["weak"],
            "Ab1!",
            "Test1!",
            "A1!",
            ""
        ]
        
        for password in short_passwords:
            is_valid, error = validate_password_strength(password)
            assert is_valid is False, f"Password '{password}' should be invalid"
            assert "najmanje 8 karaktera" in error
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_validate_password_strength_no_uppercase(self):
        """Test password strength validation for passwords without uppercase"""
        passwords_without_uppercase = [
            "password123!",
            "mypassword1!",
            "test1234!@#"
        ]
        
        for password in passwords_without_uppercase:
            is_valid, error = validate_password_strength(password)
            assert is_valid is False
            assert "veliko slovo" in error
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_validate_password_strength_no_lowercase(self):
        """Test password strength validation for passwords without lowercase"""
        passwords_without_lowercase = [
            "PASSWORD123!",
            "MYPASSWORD1!",
            "TEST1234!@#"
        ]
        
        for password in passwords_without_lowercase:
            is_valid, error = validate_password_strength(password)
            assert is_valid is False
            assert "malo slovo" in error
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_validate_password_strength_no_digit(self):
        """Test password strength validation for passwords without digits"""
        passwords_without_digits = [
            "Password!@#",
            "MyPassword!",
            "TestPassword!@#"
        ]
        
        for password in passwords_without_digits:
            is_valid, error = validate_password_strength(password)
            assert is_valid is False
            assert "broj" in error
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_validate_password_strength_no_special(self):
        """Test password strength validation for passwords without special characters"""
        passwords_without_special = [
            "Password123",
            "MyPassword123",
            "TestPassword123"
        ]
        
        for password in passwords_without_special:
            is_valid, error = validate_password_strength(password)
            assert is_valid is False
            assert "specijalni karakter" in error
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_validate_password_strength_edge_cases(self, sample_passwords):
        """Test password strength validation edge cases"""
        # Empty password
        is_valid, error = validate_password_strength(sample_passwords["empty"])
        assert is_valid is False
        assert "najmanje 8 karaktera" in error
        
        # Whitespace only
        is_valid, error = validate_password_strength(sample_passwords["whitespace"])
        assert is_valid is False
        
        # Exactly 8 characters but valid
        is_valid, error = validate_password_strength("Abcd123!")
        assert is_valid is True
        assert error == ""
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_unicode_password_support(self, sample_passwords):
        """Test support for unicode characters in passwords"""
        unicode_password = sample_passwords["unicode"]
        
        # Should hash without issues
        hashed = hash_password(unicode_password)
        assert isinstance(hashed, str)
        
        # Should verify correctly
        assert verify_password(unicode_password, hashed) is True
        
        # Wrong unicode should not verify
        assert verify_password("Šifra456!@#", hashed) is False
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_password_security_performance(self, sample_passwords):
        """Test password operations performance"""
        import time
        
        password = sample_passwords["strong"]
        
        # Hashing should be reasonably fast but not too fast (security)
        start_time = time.time()
        hashed = hash_password(password)
        hash_time = time.time() - start_time
        
        # Should take some time (bcrypt rounds=12) but not too long
        assert 0.01 < hash_time < 2.0, f"Hash time {hash_time} seems unusual"
        
        # Verification should be fast
        start_time = time.time()
        verify_password(password, hashed)
        verify_time = time.time() - start_time
        
        assert verify_time < 1.0, f"Verify time {verify_time} too slow"
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_password_special_characters_validation(self):
        """Test all supported special characters"""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        base_password = "Password123"
        
        for char in special_chars:
            password_with_char = base_password + char
            is_valid, error = validate_password_strength(password_with_char)
            assert is_valid is True, f"Password with '{char}' should be valid"
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_password_hash_consistency(self, sample_passwords):
        """Test that same password always verifies against its hash"""
        password = sample_passwords["strong"]
        
        # Generate hash
        hashed = hash_password(password)
        
        # Verify multiple times
        for _ in range(5):
            assert verify_password(password, hashed) is True
        
        # Wrong password should consistently fail
        for _ in range(5):
            assert verify_password("wrong", hashed) is False