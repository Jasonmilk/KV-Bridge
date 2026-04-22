import hashlib
import re
import os
from typing import Optional
import tiktoken

# Global tokenizer instance (lazy loaded)
_tokenizer: Optional[tiktoken.Encoding] = None

VFD_HANDLE_PATTERN = re.compile(r"\{@ref:\s*([^}]+)\}")

def get_tokenizer() -> tiktoken.Encoding:
    """Get or initialize the tokenizer (cl100k base for cross-model compatibility)."""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer

def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text string."""
    if not text:
        return 0
    tokenizer = get_tokenizer()
    return len(tokenizer.encode(text))

def sha256_text(text: str) -> str:
    """Compute SHA256 hash of a text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def sha256_file(file_path: str) -> str:
    """Compute SHA256 hash of a file's content."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def extract_path_from_handle(handle: str) -> str:
    """Extract the file path from a vFD handle string.
    
    Args:
        handle: vFD handle string, e.g., "{@ref: project_uuid/src/main.py}"
    
    Returns:
        The extracted file path.
    
    Raises:
        ValueError: If the handle format is invalid.
    """
    match = VFD_HANDLE_PATTERN.match(handle.strip())
    if not match:
        raise ValueError(f"Invalid vFD handle format: {handle}")
    return match.group(1).strip()

def generate_span_id() -> str:
    """Generate a random 8-byte span ID in hex format."""
    return os.urandom(8).hex()
