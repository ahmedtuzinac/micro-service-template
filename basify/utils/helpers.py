import uuid
from datetime import datetime, timezone


def generate_uuid() -> str:
    """
    Generiše UUID4 string
    """
    return str(uuid.uuid4())


def current_timestamp() -> datetime:
    """
    Vraća trenutni timestamp sa UTC timezone
    """
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    """
    Kreira slug od teksta
    """
    import re
    
    # Convert to lowercase
    slug = text.lower()
    
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    
    # Remove special characters
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Strip hyphens from start and end
    slug = slug.strip('-')
    
    return slug