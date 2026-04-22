import os
import time
from typing import Set, List
from kv_bridge.schemas.exceptions import VFDResolutionError
from kv_bridge.common import Settings, logger
from kv_bridge.common.utils import extract_path_from_handle, sha256_file
from .indexer import VFDIndexer

class VFDAllocator:
    """Manage virtual file descriptor lifecycle."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._indexer = VFDIndexer(settings.vfd_index_path)
        self._locked_handles: Set[str] = set()  # Generation-locked handles

    def _compute_eviction_score(self, record: Dict) -> float:
        """Compute hybrid eviction score based on policy."""
        now = int(time.time())
        if self.settings.lru_policy == "lru":
            return float(now - record["last_accessed"])
        elif self.settings.lru_policy == "lfu":
            return -float(record["access_frequency"])
        else:  # hybrid
            return (now - record["last_accessed"]) / (record["access_frequency"] + 1)

    async def resolve(self, handle: str) -> str:
        """
        Expand a vFD handle to its current file content.

        Args:
            handle: vFD handle string, e.g., "{@ref: project_uuid/src/main.py}"

        Returns:
            Current file content as string.

        Raises:
            VFDResolutionError: If handle cannot be resolved.
        """
        try:
            # 1. Parse handle and extract file path
            path = extract_path_from_handle(handle)
            
            # Resolve absolute path (relative to current working directory for now)
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                raise VFDResolutionError(f"File not found for vFD handle: {path}")

            # 2. Query SQLite for existing record
            record = await self._indexer.get(handle)
            current_hash = sha256_file(abs_path)
            file_size = os.path.getsize(abs_path)

            if record:
                # 3. Check if file content changed
                if current_hash != record["content_hash"]:
                    logger.info(
                        "vFD content changed, updating index",
                        handle=handle,
                        old_hash=record["content_hash"],
                        new_hash=current_hash
                    )
                    await self._indexer.update(
                        handle, 
                        content_hash=current_hash, 
                        size_bytes=file_size
                    )
            else:
                # 4. Insert new record
                logger.info("New vFD handle registered", handle=handle)
                await self._indexer.insert(
                    handle,
                    content_hash=current_hash,
                    file_path=abs_path,
                    size_bytes=file_size
                )

            # 5. Read file content
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 6. Update access timestamp (for LRU/LFU)
            await self._indexer.touch(handle)

            logger.debug("vFD handle resolved", handle=handle, size_bytes=file_size)
            return content

        except Exception as e:
            if isinstance(e, VFDResolutionError):
                raise
            logger.error("Failed to resolve vFD handle", handle=handle, error=str(e))
            raise VFDResolutionError(f"Failed to resolve vFD handle: {str(e)}") from e

    def lock_generation(self, handles: List[str]) -> None:
        """Lock handles for the duration of one generation (request)."""
        self._locked_handles.update(handles)
        logger.debug("Locked vFD handles for generation", handles=list(self._locked_handles))

    def unlock_generation(self) -> None:
        """Release all generation locks, allowing LRU eviction."""
        logger.debug("Unlocked vFD handles for generation", handles=list(self._locked_handles))
        self._locked_handles.clear()

    async def evict_lru_if_needed(self) -> None:
        """
        Perform hybrid LRU/LFU eviction at request boundary.
        Never evict handles currently locked in _locked_handles.
        """
        current_count = await self._indexer.count()
        if current_count <= self.settings.lru_max_size:
            return

        # Get candidates for eviction
        to_evict = current_count - self.settings.lru_max_size
        candidates = await self._indexer.get_candidates_for_eviction(limit=to_evict)

        # Sort candidates by eviction score
        candidates.sort(key=self._compute_eviction_score)

        evicted = 0
        for record in candidates:
            if evicted >= to_evict:
                break
            if record["handle"] not in self._locked_handles:
                await self._indexer.delete(record["handle"])
                evicted += 1
                logger.info(
                    "Evicted vFD entry",
                    handle=record["handle"],
                    policy=self.settings.lru_policy,
                    score=self._compute_eviction_score(record)
                )

        if evicted > 0:
            remaining = await self._indexer.count()
            logger.info(
                "vFD eviction complete", 
                evicted_count=evicted, 
                remaining_count=remaining,
                policy=self.settings.lru_policy
            )
