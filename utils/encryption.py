"""Encryption utilities."""

import hashlib


def md5(content: str) -> str:
    """Generate MD5 hash of content."""
    return hashlib.md5(content.encode()).hexdigest()


def sha256(content: str) -> str:
    """Generate SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()
