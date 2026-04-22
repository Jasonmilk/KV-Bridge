import aiosqlite
import time
from pathlib import Path
from typing import Optional, List, Dict

class VFDIndexer:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn: Optional[aiosqlite.Connection] = None

    async def _init_db(self):
        """Initialize database schema if not exists, with WAL mode."""
        conn = await self._get_conn()
        
        # Enable WAL mode for concurrent access
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        await conn.execute("PRAGMA cache_size=-64000;")
        
        # Create main table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vfd_index (
                handle TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                file_path TEXT NOT NULL,
                last_accessed INTEGER NOT NULL,
                access_count INTEGER DEFAULT 1,
                access_frequency INTEGER DEFAULT 1,
                size_bytes INTEGER
            )
        """)
        
        # Migrate existing database: add access_frequency column if missing
        try:
            await conn.execute("ALTER TABLE vfd_index ADD COLUMN access_frequency INTEGER DEFAULT 1;")
            await conn.commit()
        except aiosqlite.OperationalError:
            # Column already exists, ignore
            pass
        
        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON vfd_index(content_hash)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON vfd_index(last_accessed)")
        await conn.commit()

    async def _get_conn(self) -> aiosqlite.Connection:
        """Get or create the async connection."""
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            await self._init_db()
        return self._conn

    async def get(self, handle: str) -> Optional[Dict]:
        """Get a record by handle."""
        conn = await self._get_conn()
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM vfd_index WHERE handle = ?", (handle,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def insert(self, handle: str, content_hash: str, file_path: str, size_bytes: int):
        """Insert a new record."""
        now = int(time.time())
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO vfd_index 
            (handle, content_hash, file_path, last_accessed, access_count, access_frequency, size_bytes)
            VALUES (?, ?, ?, ?, 1, 1, ?)
        """, (handle, content_hash, file_path, now, size_bytes))
        await conn.commit()

    async def update(self, handle: str, **kwargs):
        """Update fields of an existing record."""
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [handle]
        conn = await self._get_conn()
        await conn.execute(f"UPDATE vfd_index SET {set_clause} WHERE handle = ?", values)
        await conn.commit()

    async def touch(self, handle: str):
        """Update last_accessed timestamp and increment frequency."""
        now = int(time.time())
        conn = await self._get_conn()
        await conn.execute("""
            UPDATE vfd_index 
            SET last_accessed = ?, 
                access_count = access_count + 1,
                access_frequency = access_frequency + 1
            WHERE handle = ?
        """, (now, handle))
        await conn.commit()

    async def count(self) -> int:
        """Get total number of records."""
        conn = await self._get_conn()
        async with conn.execute("SELECT COUNT(*) FROM vfd_index") as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def get_candidates_for_eviction(self, limit: int) -> List[Dict]:
        """Get records sorted by hybrid eviction score."""
        conn = await self._get_conn()
        conn.row_factory = aiosqlite.Row
        async with conn.execute("""
            SELECT * FROM vfd_index 
            ORDER BY last_accessed ASC, access_frequency DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return [dict(row) async for row in cursor]

    async def delete(self, handle: str):
        """Delete a record by handle."""
        conn = await self._get_conn()
        await conn.execute("DELETE FROM vfd_index WHERE handle = ?", (handle,))
        await conn.commit()

    async def close(self):
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
