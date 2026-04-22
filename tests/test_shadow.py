import pytest
from datetime import datetime, timedelta
from kv_bridge.core.shadow.radix_tree import ShadowRadixTree, RadixNode

def test_shadow_lookup_insert(mock_settings):
    tree = ShadowRadixTree(mock_settings)
    prefix = "test prefix"
    prefix_hash = "test_hash"
    
    node = tree.insert_or_update(prefix, prefix_hash)
    assert node.prefix_hash == prefix_hash
    assert node.access_count == 1
    
    found = tree.lookup(prefix)
    assert found is not None
    assert found.prefix_hash == prefix_hash

def test_shadow_lookup_miss(mock_settings):
    tree = ShadowRadixTree(mock_settings)
    found = tree.lookup("nonexistent")
    assert found is None

def test_shadow_expired(mock_settings):
    mock_settings.shadow_ttl_seconds = 1
    tree = ShadowRadixTree(mock_settings)
    prefix = "test"
    tree.insert_or_update(prefix, "hash")
    
    # Manually set last_accessed to expire it
    node = tree.lookup(prefix)
    node.last_accessed = datetime.now() - timedelta(seconds=2)
    
    found = tree.lookup(prefix)
    assert found is None  # Expired

def test_should_piggyback(mock_settings):
    tree = ShadowRadixTree(mock_settings)
    prefix = "test"
    node = tree.insert_or_update(prefix, "hash")
    
    # Add multiple recent accesses
    for _ in range(3):
        node.record_access()
    
    # Set TTL to expire soon
    node.last_accessed = datetime.now() - timedelta(seconds=3500)  # 10s remaining
    
    assert tree.should_piggyback(node) is True

def test_should_not_piggyback_ttl_ok(mock_settings):
    tree = ShadowRadixTree(mock_settings)
    prefix = "test"
    node = tree.insert_or_update(prefix, "hash")
    assert tree.should_piggyback(node) is False  # TTL still plenty
