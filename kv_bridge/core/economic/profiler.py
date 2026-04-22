from typing import List, Tuple
from kv_bridge.schemas.prompt import PromptBlock
from kv_bridge.common import Settings, logger
from kv_bridge.common.utils import estimate_tokens

class EconomicProfiler:
    """Decide whether reordering is economically justified."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def should_reorder(self, blocks: List[PromptBlock], total_tokens: int) -> Tuple[bool, int]:
        """
        Determine if reordering should proceed.

        Args:
            blocks: Original prompt blocks.
            total_tokens: Estimated total token count.

        Returns:
            Tuple of (should_reorder: bool, estimated_savings: int)
        """
        # Condition 1: Skip if total tokens below threshold (short context)
        if total_tokens < self.settings.skip_reorder_below_tokens:
            logger.info(
                "Skipping reorder: short context",
                total_tokens=total_tokens,
                threshold=self.settings.skip_reorder_below_tokens
            )
            return False, 0

        # Condition 2: Compute estimated savings from static portion
        static_tokens = sum(
            estimate_tokens(b.content) for b in blocks if b.volatility.score <= 1
        )
        estimated_savings = static_tokens

        # Condition 3: Savings must exceed minimum threshold
        if estimated_savings < self.settings.min_savings_threshold:
            logger.info(
                "Skipping reorder: insufficient savings",
                estimated_savings=estimated_savings,
                threshold=self.settings.min_savings_threshold
            )
            return False, estimated_savings

        # Condition 4: Explicit barrier permits safe reordering
        if any(b.contains_barrier for b in blocks):
            logger.info(
                "Reorder permitted: explicit barrier present",
                estimated_savings=estimated_savings
            )
            return True, estimated_savings

        # Condition 5: All blocks are system or vFD (safe to reorder)
        if all(b.role in ("system", "vfd") for b in blocks):
            logger.info(
                "Reorder permitted: all static blocks",
                estimated_savings=estimated_savings
            )
            return True, estimated_savings

        # Condition 6: User content present, conservative: do not reorder
        logger.info(
            "Skipping reorder: user content present without barrier",
            estimated_savings=estimated_savings
        )
        return False, estimated_savings
