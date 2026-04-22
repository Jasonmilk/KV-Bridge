class KVBridgeBaseError(Exception):
    """Base class for all KV-Bridge exceptions."""
    pass

class CompilationError(KVBridgeBaseError):
    """Iceberg compiler failed to process prompt."""
    pass

class VFDResolutionError(KVBridgeBaseError):
    """vFD handle could not be resolved to actual content."""
    pass

class BackendUnavailableError(KVBridgeBaseError):
    """LLM backend is unhealthy or unreachable."""
    pass

class CacheVerificationMismatch(KVBridgeBaseError):
    """Shadow tree prediction did not match API reported cache hit."""
    pass
