import pytest
import tempfile
import os
from kv_bridge.core.vfd.allocator import VFDAllocator
from kv_bridge.schemas.exceptions import VFDResolutionError

def test_vfd_resolve_file(mock_settings):
    # Create a temp test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("test content")
        temp_path = f.name
    
    try:
        allocator = VFDAllocator(mock_settings)
        handle = f"{{@ref: {temp_path}}}"
        content = allocator.resolve(handle)
        assert content == "test content"
        
        # Check it's in the index
        assert allocator._indexer.count() == 1
    finally:
        os.unlink(temp_path)

def test_vfd_lru_eviction(mock_settings):
    mock_settings.lru_max_size = 2
    
    # Create temp files
    files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(f"content {i}")
            files.append(f.name)
    
    try:
        allocator = VFDAllocator(mock_settings)
        
        # Resolve all 3 files
        for f in files:
            handle = f"{{@ref: {f}}}"
            allocator.resolve(handle)
        
        # After eviction, should have only 2 entries
        allocator.evict_lru_if_needed()
        assert allocator._indexer.count() == 2
        
        # The oldest one should be evicted
        oldest_handle = f"{{@ref: {files[0]}}}"
        assert allocator._indexer.get(oldest_handle) is None
    finally:
        for f in files:
            os.unlink(f)

def test_vfd_locked_handles_not_evicted(mock_settings):
    mock_settings.lru_max_size = 2
    
    files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(f"content {i}")
            files.append(f.name)
    
    try:
        allocator = VFDAllocator(mock_settings)
        
        # Resolve all
        handles = [f"{{@ref: {f}}}" for f in files]
        for h in handles:
            allocator.resolve(h)
        
        # Lock the oldest one
        allocator.lock_generation([handles[0]])
        
        # Evict
        allocator.evict_lru_if_needed()
        
        # Oldest is locked, so the next one gets evicted
        assert allocator._indexer.get(handles[0]) is not None  # Locked, not evicted
        assert allocator._indexer.get(handles[1]) is None  # Evicted instead
    finally:
        for f in files:
            os.unlink(f)

def test_vfd_invalid_handle(mock_settings):
    allocator = VFDAllocator(mock_settings)
    with pytest.raises(VFDResolutionError):
        allocator.resolve("{@ref: non_existent_file.txt}")
