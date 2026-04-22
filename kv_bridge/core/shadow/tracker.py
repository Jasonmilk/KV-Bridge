from typing import Optional
from datetime import datetime
from kv_bridge.common import Settings, logger
from .radix_tree import ShadowRadixTree, RadixNode

class ShadowTracker:
    """Tracks cache hit predictions and reconciles with actual results."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tree = ShadowRadixTree(settings)

    def predict_hit(self, prefix_text: str, prefix_hash: str) -> Tuple[bool, Optional[RadixNode]]:
        """
        Predict if a prefix will hit the backend cache.
        
        Args:
            prefix_text: The static prefix text
            prefix_hash: Hash of the static prefix
            
        Returns:
            Tuple of (hit_predicted: bool, node: Optional[RadixNode])
        """
        node = self.tree.lookup(prefix_text)
        if node and node.prefix_hash == prefix_hash:
            logger.debug(
                "Shadow tree predicted cache hit",
                prefix_hash=prefix_hash,
                ttl_remaining=node.ttl_remaining
            )
            return True, node
        logger.debug("Shadow tree predicted cache miss", prefix_hash=prefix_hash)
        return False, None

    def record_result(self, prefix_text: str, prefix_hash: str, hit_verified: bool) -> None:
        """
        Record the actual cache hit result to update the shadow tree.
        
        Args:
            prefix_text: The static prefix text
            prefix_hash: Hash of the static prefix
            hit_verified: Whether the backend actually reported a hit
        """
        if hit_verified:
            # Insert or update the node in the shadow tree
            node = self.tree.insert_or_update(prefix_text, prefix_hash)
            logger.info(
                "Recorded cache hit in shadow tree",
                prefix_hash=prefix_hash,
                access_count=node.access_count,
                ttl_remaining=node.ttl_remaining
            )

            # Check if we need to piggyback refresh
            if self.tree.should_piggyback(node):
                logger.info(
                    "Piggyback refresh triggered for prefix",
                    prefix_hash=prefix_hash
                )
                # Piggyback refresh is handled automatically by updating last_accessed
                # which extends the TTL
        else:
            logger.debug(
                "Recorded cache miss in shadow tree",
                prefix_hash=prefix_hash
            )

    def get_stats(self) -> dict:
        """Get shadow tree statistics for monitoring."""
        # Simple count of nodes
        def count_nodes(node: RadixNode) -> int:
            return 1 + sum(count_nodes(child) for child in node.children.values())
        
        total_nodes = count_nodes(self.tree.root) - 1  # exclude root
        return {
            "total_prefixes": total_nodes,
            "ttl_seconds": self.settings.shadow_ttl_seconds
        }
