"""Stable 8-char content hashes. Same algorithm gbrain uses for best.md."""
import hashlib

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
