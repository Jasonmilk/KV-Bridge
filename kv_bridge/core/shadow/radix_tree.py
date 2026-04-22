from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from kv_bridge.common import Settings
from kv_bridge.common.utils import get_tokenizer

@dataclass
class RadixNode:
    prefix_hash: str
    edge_tokens: List[int] = field(default_factory=list)  # Token sequence on this edge (path compression)
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    total_access_count: int = 0  # LFU: cumulative accesses
    access_timestamps: List[datetime] = field(default_factory=list)
    ttl_seconds: int = 3600  # Default TTL
    children: Dict[int, "RadixNode"] = field(default_factory=dict)  # Keyed by first token of edge

    @property
    def ttl_remaining(self) -> int:
        elapsed = (datetime.now() - self.last_accessed).total_seconds()
        return max(0, self.ttl_seconds - int(elapsed))

    @property
    def is_expired(self) -> bool:
        return self.ttl_remaining == 0

    def record_access(self) -> None:
        """Record an access event, updating timestamps and counters."""
        now = datetime.now()
        self.last_accessed = now
        self.access_count += 1
        self.total_access_count += 1
        self.access_timestamps.append(now)
        # Clean up old timestamps to save memory
        cutoff = now - timedelta(seconds=self.ttl_seconds)
        self.access_timestamps = [t for t in self.access_timestamps if t > cutoff]

class ShadowRadixTree:
    """Token-level path-compressed Radix Tree for prefix cache prediction."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tokenizer = get_tokenizer()
        self.root = RadixNode(
            prefix_hash="",
            created_at=datetime.now(), 
            last_accessed=datetime.now()
        )

    def _tokenize(self, text: str) -> List[int]:
        """Tokenize text into token IDs."""
        return self.tokenizer.encode(text)

    def lookup(self, prefix_text: str) -> Optional[RadixNode]:
        """
        Find the deepest node matching the given prefix, using token-level path compression.
        
        Args:
            prefix_text: The prefix text to look up
            
        Returns:
            RadixNode if found and not expired, else None.
        """
        tokens = self._tokenize(prefix_text)
        node = self.root
        i = 0
        
        while i < len(tokens):
            first_token = tokens[i]
            if first_token not in node.children:
                return None
                
            child = node.children[first_token]
            edge_len = len(child.edge_tokens)
            
            # Check if the edge matches the remaining tokens
            if i + edge_len > len(tokens):
                return None  # Prefix shorter than edge, no match
            if tokens[i:i+edge_len] != child.edge_tokens:
                return None  # Edge tokens don't match
                
            node = child
            i += edge_len
            
        return node if not node.is_expired else None

    def insert_or_update(self, prefix_text: str, prefix_hash: str) -> RadixNode:
        """Insert new prefix or update access time of existing node."""
        tokens = self._tokenize(prefix_text)
        node = self.root
        i = 0
        
        while i < len(tokens):
            first_token = tokens[i]
            if first_token not in node.children:
                # Create new node with the remaining tokens as edge
                edge_tokens = tokens[i:]
                child = RadixNode(
                    prefix_hash="",
                    edge_tokens=edge_tokens,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    ttl_seconds=self.settings.shadow_ttl_seconds
                )
                node.children[first_token] = child
                node = child
                i = len(tokens)
            else:
                child = node.children[first_token]
                edge_len = len(child.edge_tokens)
                
                # Check if we can consume the entire edge
                if i + edge_len <= len(tokens) and tokens[i:i+edge_len] == child.edge_tokens:
                    # Entire edge matches, move forward
                    node = child
                    i += edge_len
                else:
                    # Need to split the edge
                    # 1. Find the longest common prefix
                    common = 0
                    while common < edge_len and i + common < len(tokens) and tokens[i+common] == child.edge_tokens[common]:
                        common += 1
                        
                    # 2. Create new intermediate node for the common part
                    new_node = RadixNode(
                        prefix_hash="",
                        edge_tokens=child.edge_tokens[:common],
                        created_at=datetime.now(),
                        last_accessed=datetime.now(),
                        ttl_seconds=self.settings.shadow_ttl_seconds
                    )
                    node.children[first_token] = new_node
                    
                    # 3. Update old child to be child of new node, with remaining edge
                    child.edge_tokens = child.edge_tokens[common:]
                    new_node.children[child.edge_tokens[0]] = child
                    
                    # 4. If there are remaining tokens, create new node for them
                    if i + common < len(tokens):
                        remaining_tokens = tokens[i+common:]
                        new_child = RadixNode(
                            prefix_hash="",
                            edge_tokens=remaining_tokens,
                            created_at=datetime.now(),
                            last_accessed=datetime.now(),
                            ttl_seconds=self.settings.shadow_ttl_seconds
                        )
                        new_node.children[remaining_tokens[0]] = new_child
                        node = new_child
                    else:
                        node = new_node
                    i = len(tokens)
        
        # Update leaf node
        node.prefix_hash = prefix_hash
        node.record_access()
        return node

    def should_piggyback(self, node: RadixNode) -> bool:
        """
        Decide whether to refresh this prefix using a piggyback request.

        Conditions:
        1. TTL remaining < 120 seconds.
        2. At least 3 accesses in last 10 minutes.
        3. Keep-alive cost < 10% of recompute cost.
        """
        # Condition 1: TTL is about to expire
        if node.ttl_remaining > 120:
            return False

        # Condition 2: Recent high access frequency
        recent_window = datetime.now() - timedelta(minutes=10)
        recent_hits = sum(1 for t in node.access_timestamps if t > recent_window)
        if recent_hits < 3:
            return False

        # Condition 3: Cost ratio check
        return True

