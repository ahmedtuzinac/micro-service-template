import re
from typing import Optional


def validate_email(email: str) -> bool:
    """
    Validira email adresu
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """
    Validira korisničko ime
    - Između 3 i 30 karaktera
    - Može da sadrži slova, brojevi, _ i -
    """
    if len(username) < 3 or len(username) > 30:
        return False
    
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, username))


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validira šifru
    Vraća (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, None