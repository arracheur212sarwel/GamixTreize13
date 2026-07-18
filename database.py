"""
database.py
Couche d'accès unique à la base SQLite (via aiosqlite) pour les trois
modules du bot : Modération, Smash or Pass, Tickets.

Une seule connexion partagée, une seule fois data/bot.db. Tables préfixées
par module pour éviter toute collision de noms.
"""

import os
import time
from typing import Any, Dict, List, Optional

import aiosqlite

DB_PATH = os.path.join("data", "bot.db")
_db: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Retourne la connexion persistante, l'initialise si nécessaire."""
    global _db
    if _db is None:
        os.makedirs("data", exist_ok=True)
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL;")
        await _create_tables(_db)
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def init_db() -> None:
    """Initialise la base de données au démarrage."""
    await get_db()


async def _create_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            logs_channel INTEGER,
            staff_role INTEGER,
            mute_role INTEGER,
            embed_color TEXT DEFAULT '#57F287',
            language TEXT DEFAULT 'fr'
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS punishments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            duration INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS sop_posts (
            message_id INTEGER PRIMARY KEY,
            thread_id INTEGER NOT NULL,
            embed_message_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            end_at TEXT NOT NULL,
            closed INTEGER NOT NULL DEFAULT 0
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sop_votes (
            message_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            vote TEXT NOT NULL CHECK (vote IN ('smash', 'pass')),
            PRIMARY KEY (message_id, user_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            claimed_by INTEGER,
            created_at INTEGER NOT NULL,
            closed_at INTEGER,
            reopened_at INTEGER
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ticket_cooldowns (
            user_id INTEGER PRIMARY KEY,
            expires_at INTEGER NOT NULL
        )
    """)

    # ------------------------------------------------- Rôles par affinité
    await db.execute("""
        CREATE TABLE IF NOT EXISTS voice_activity (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            total_seconds INTEGER NOT NULL DEFAULT 0,
            session_start INTEGER,
            proposal_count INTEGER NOT NULL DEFAULT 0,
            promoted INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    cursor = await db.execute("PRAGMA table_info(voice_activity)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "proposal_count" not in columns:
        await db.execute("ALTER TABLE voice_activity ADD COLUMN proposal_count INTEGER NOT NULL DEFAULT 0")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS message_activity (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    await db.commit()



async def get_guild_config(guild_id: int) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None



async def sop_create_post(**kwargs) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO sop_posts (
            message_id, thread_id, embed_message_id, guild_id, channel_id,
            author_id, author_name, created_at, end_at, closed
        ) VALUES (:message_id, :thread_id, :embed_message_id, :guild_id, :channel_id,
                  :author_id, :author_name, :created_at, :end_at, 0)
        """,
        kwargs,
    )
    await db.commit()


async def sop_get_post(message_id: int) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sop_posts WHERE message_id = ?", (message_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def sop_get_active_posts() -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sop_posts WHERE closed = 0")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def sop_get_expired_posts(now_iso: str) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM sop_posts WHERE closed = 0 AND end_at <= ?", (now_iso,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def sop_close_post(message_id: int) -> None:
    db = await get_db()
    await db.execute("UPDATE sop_posts SET closed = 1 WHERE message_id = ?", (message_id,))
    await db.commit()


async def sop_get_top_posts(limit: int = 10) -> List[Dict[str, Any]]:
    db = await get_db()
    query = """
        SELECT p.message_id, p.guild_id, p.channel_id, p.author_id, p.author_name,
               COALESCE(SUM(CASE WHEN v.vote = 'smash' THEN 1 ELSE 0 END), 0) AS smash_count,
               COALESCE(SUM(CASE WHEN v.vote = 'pass' THEN 1 ELSE 0 END), 0) AS pass_count
        FROM sop_posts p
        LEFT JOIN sop_votes v ON v.message_id = p.message_id
        GROUP BY p.message_id
        ORDER BY smash_count DESC, pass_count ASC
        LIMIT ?
    """
    cursor = await db.execute(query, (limit,))
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def sop_get_user_vote(message_id: int, user_id: int) -> Optional[str]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT vote FROM sop_votes WHERE message_id = ? AND user_id = ?", (message_id, user_id)
    )
    row = await cursor.fetchone()
    return row["vote"] if row else None


async def sop_set_vote(message_id: int, user_id: int, vote: str) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO sop_votes (message_id, user_id, vote) VALUES (?, ?, ?)
        ON CONFLICT(message_id, user_id) DO UPDATE SET vote = excluded.vote
        """,
        (message_id, user_id, vote),
    )
    await db.commit()


async def sop_get_vote_counts(message_id: int) -> Dict[str, int]:
    db = await get_db()
    counts = {"smash": 0, "pass": 0}
    cursor = await db.execute(
        "SELECT vote, COUNT(*) as c FROM sop_votes WHERE message_id = ? GROUP BY vote",
        (message_id,),
    )
    rows = await cursor.fetchall()
    for row in rows:
        counts[row["vote"]] = row["c"]
    return counts



async def ticket_create(channel_id: int, guild_id: int, owner_id: int, category: str) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO tickets (channel_id, guild_id, owner_id, category, status, created_at)
        VALUES (?, ?, ?, ?, 'open', ?)
        """,
        (channel_id, guild_id, owner_id, category, int(time.time() * 1000)),
    )
    await db.commit()


async def ticket_get(channel_id: int) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def ticket_get_open_by_owner(owner_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM tickets WHERE owner_id = ? AND guild_id = ? AND status = 'open'",
        (owner_id, guild_id),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def ticket_close(channel_id: int) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE tickets SET status = 'closed', closed_at = ? WHERE channel_id = ?",
        (int(time.time() * 1000), channel_id),
    )
    await db.commit()


async def ticket_reopen(channel_id: int) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE tickets SET status = 'open', reopened_at = ? WHERE channel_id = ?",
        (int(time.time() * 1000), channel_id),
    )
    await db.commit()


async def ticket_claim(channel_id: int, staff_id: int) -> None:
    db = await get_db()
    await db.execute("UPDATE tickets SET claimed_by = ? WHERE channel_id = ?", (staff_id, channel_id))
    await db.commit()


async def ticket_delete(channel_id: int) -> None:
    db = await get_db()
    await db.execute("DELETE FROM tickets WHERE channel_id = ?", (channel_id,))
    await db.commit()


async def ticket_is_on_cooldown(user_id: int) -> bool:
    db = await get_db()
    cursor = await db.execute("SELECT expires_at FROM ticket_cooldowns WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    if not row:
        return False
    return row["expires_at"] > int(time.time() * 1000)


async def ticket_get_remaining_cooldown(user_id: int) -> int:
    db = await get_db()
    cursor = await db.execute("SELECT expires_at FROM ticket_cooldowns WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    if not row:
        return 0
    return max(0, row["expires_at"] - int(time.time() * 1000))


async def ticket_set_cooldown(user_id: int, duration_ms: int) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO ticket_cooldowns (user_id, expires_at) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET expires_at = excluded.expires_at
        """,
        (user_id, int(time.time() * 1000) + duration_ms),
    )
    await db.commit()


# ======================================================================
# Rôles par affinité (activité vocale)
# ======================================================================

async def voice_get_or_create(user_id: int, guild_id: int) -> Dict[str, Any]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM voice_activity WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    await db.execute(
        "INSERT INTO voice_activity (user_id, guild_id, total_seconds, session_start, proposal_count, promoted) "
        "VALUES (?, ?, 0, NULL, 0, 0)",
        (user_id, guild_id),
    )
    await db.commit()
    return {
        "user_id": user_id, "guild_id": guild_id, "total_seconds": 0,
        "session_start": None, "proposal_count": 0, "promoted": 0,
    }


async def voice_start_session(user_id: int, guild_id: int, started_at: int) -> None:
    db = await get_db()
    await voice_get_or_create(user_id, guild_id)
    await db.execute(
        "UPDATE voice_activity SET session_start = ? WHERE user_id = ? AND guild_id = ?",
        (started_at, user_id, guild_id),
    )
    await db.commit()


async def voice_end_session(user_id: int, guild_id: int, ended_at: int) -> Optional[int]:
    """Clôture la session en cours, ajoute la durée à total_seconds, renvoie le nouveau total (ou None si pas de session)."""
    db = await get_db()
    row = await voice_get_or_create(user_id, guild_id)
    if not row["session_start"]:
        return None
    elapsed = max(0, ended_at - row["session_start"])
    new_total = row["total_seconds"] + elapsed
    await db.execute(
        "UPDATE voice_activity SET total_seconds = ?, session_start = NULL WHERE user_id = ? AND guild_id = ?",
        (new_total, user_id, guild_id),
    )
    await db.commit()
    return new_total


async def voice_set_proposal_count(user_id: int, guild_id: int, count: int) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE voice_activity SET proposal_count = ? WHERE user_id = ? AND guild_id = ?", (count, user_id, guild_id)
    )
    await db.commit()


async def voice_mark_promoted(user_id: int, guild_id: int) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE voice_activity SET promoted = 1 WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)
    )
    await db.commit()


# ======================================================================
# Comptage de messages (pour /topmsg)
# ======================================================================

async def message_increment(user_id: int, guild_id: int) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO message_activity (user_id, guild_id, message_count) VALUES (?, ?, 1)
        ON CONFLICT(user_id, guild_id) DO UPDATE SET message_count = message_count + 1
        """,
        (user_id, guild_id),
    )
    await db.commit()


async def message_get_count(user_id: int, guild_id: int) -> int:
    db = await get_db()
    cursor = await db.execute(
        "SELECT message_count FROM message_activity WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)
    )
    row = await cursor.fetchone()
    return row["message_count"] if row else 0


async def message_get_top(guild_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT user_id, message_count FROM message_activity WHERE guild_id = ? ORDER BY message_count DESC LIMIT ?",
        (guild_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def voice_get_top(guild_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT user_id, total_seconds, session_start FROM voice_activity WHERE guild_id = ? ORDER BY total_seconds DESC LIMIT ?",
        (guild_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]