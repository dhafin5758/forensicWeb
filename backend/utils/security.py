"""
Security Utilities
Authentication, authorization, and validation helpers.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
import jwt

from backend.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Bcrypt hash
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Password to verify
        hashed_password: Bcrypt hash
    
    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload to encode in token
        expires_delta: Token expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None


def generate_secure_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate a secure filename with random component.
    
    Args:
        original_filename: Original file name
        prefix: Optional prefix
    
    Returns:
        Secure filename
    """
    from pathlib import Path
    
    ext = Path(original_filename).suffix
    random_part = secrets.token_hex(16)
    
    if prefix:
        return f"{prefix}_{random_part}{ext}"
    return f"{random_part}{ext}"


def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, sha1, md5)
    
    Returns:
        Hex digest of hash
    """
    hasher = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def constant_time_compare(val1: str, val2: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.
    
    Args:
        val1: First string
        val2: Second string
    
    Returns:
        True if strings match
    """
    return hmac.compare_digest(val1, val2)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import re
    from pathlib import Path
    
    # Remove any path components
    filename = Path(filename).name
    
    # Remove non-alphanumeric characters except dots, dashes, underscores
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255-len(ext)] + ext
    
    return filename or "unnamed"


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self):
        self._requests = {}  # {key: [(timestamp, count), ...]}
    
    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key (e.g., IP address, user ID)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            True if request is allowed
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Clean old entries
        if key in self._requests:
            self._requests[key] = [
                req for req in self._requests[key]
                if req[0] > cutoff
            ]
        else:
            self._requests[key] = []
        
        # Check limit
        if len(self._requests[key]) >= max_requests:
            return False
        
        # Add request
        self._requests[key].append((now, 1))
        return True
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._requests:
            del self._requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()
