"""
Password utilities za auth-service
"""
import bcrypt


def hash_password(password: str) -> str:
    """Hash password sa bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password protiv hash-a"""
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validira strength password-a
    
    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password mora imati najmanje 8 karaktera"
    
    if not any(c.isupper() for c in password):
        return False, "Password mora imati najmanje jedno veliko slovo"
    
    if not any(c.islower() for c in password):
        return False, "Password mora imati najmanje jedno malo slovo"
    
    if not any(c.isdigit() for c in password):
        return False, "Password mora imati najmanje jedan broj"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password mora imati najmanje jedan specijalni karakter"
    
    return True, ""