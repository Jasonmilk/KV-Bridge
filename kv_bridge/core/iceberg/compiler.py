from typing import List
from kv_bridge.schemas.prompt import PromptBlock, VolatilityLevel
from kv_bridge.schemas.request import CompiledRequest
from kv_bridge.common import Settings, logger
from kv_bridge.common.utils import estimate_tokens, sha256_text
from .barrier import strip_barrier

class IcebergCompiler:
    """Compile prompt blocks into cache-optimal layout."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def compile(self, blocks: List[PromptBlock]) -> CompiledRequest:
        """
        Reorder blocks to maximize prefix cache reuse.

        Args:
            blocks: Original prompt blocks in developer-defined order.

        Returns:
            CompiledRequest with reordered blocks and cache metadata.
        """
        if not blocks:
            return CompiledRequest(
                blocks=[],
                cache_breakpoints=[],
                prefix_hash="",
                total_tokens=0,
                estimated_savings=0
            )

        # 1. Find first cache barrier
        barrier_index = None
        for i, block in enumerate(blocks):
            if block.contains_barrier:
                barrier_index = i
                # Strip barrier marker from content
                block.content = strip_barrier(block.content)
                break

        # 2. Split into reorderable and protected regions
        reorderable = blocks[:barrier_index] if barrier_index is not None else blocks
        protected = blocks[barrier_index:] if barrier_index is not None else []

        # 3. Sort reorderable blocks by volatility score ascending
        reorderable.sort(key=lambda b: b.volatility.score)

        # 4. Inject attention anchor at the head of deep iceberg layer
        if reorderable and reorderable[0].volatility.score == 0:
            anchor = PromptBlock(
                content="<|attention_anchor|>",
                volatility=VolatilityLevel(score=0, reason="attention_anchor"),
                role="system",
                source=None,
                contains_barrier=False
            )
            reorderable.insert(0, anchor)

        # 5. Compute cache breakpoints (where volatility score changes)
        breakpoints = []
        compiled_blocks = reorderable + protected
        current_score = None
        token_count = 0
        for i, block in enumerate(compiled_blocks):
            block_tokens = estimate_tokens(block.content)
            if i > 0 and block.volatility.score != current_score:
                breakpoints.append(token_count)
            current_score = block.volatility.score
            token_count += block_tokens

        # 6. Compute prefix hash of static portion (volatility score <= 1)
        static_blocks = [b for b in compiled_blocks if b.volatility.score <= 1]
        static_text = "".join(b.content for b in static_blocks)
        prefix_hash = sha256_text(static_text)

        # 7. Estimate total tokens and savings
        total_tokens = sum(estimate_tokens(b.content) for b in compiled_blocks)
        static_tokens = sum(estimate_tokens(b.content) for b in static_blocks)
        estimated_savings = static_tokens

        logger.info(
            "Iceberg compilation complete",
            total_blocks=len(blocks),
            reorderable_blocks=len(reorderable),
            protected_blocks=len(protected),
            prefix_hash=prefix_hash,
            estimated_savings=estimated_savings,
            breakpoints_count=len(breakpoints)
        )

        return CompiledRequest(
            blocks=compiled_blocks,
            cache_breakpoints=breakpoints,
            prefix_hash=prefix_hash,
            total_tokens=total_tokens,
            estimated_savings=estimated_savings,
        )
