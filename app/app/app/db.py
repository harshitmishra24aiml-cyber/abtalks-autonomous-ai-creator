import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "agent.db"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                persona_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS topics (
                topic_key TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                discovered_at TEXT NOT NULL,
                score REAL NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                text TEXT NOT NULL,
                rationale TEXT NOT NULL,
                sources TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_posts_agent_created
            ON posts(agent_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_topics_agent
            ON topics(agent_id);
        """)


def save_agent(
    agent_id: str,
    name: str,
    domain: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agents(
                agent_id,
                persona_name,
                domain,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                agent_id,
                name,
                domain,
                created_at,
            ),
        )


def get_agent(agent_id: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM agents
            WHERE agent_id = ?
            """,
            (agent_id,),
        ).fetchone()


def get_active_agents() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM agents
            WHERE active = 1
            """
        ).fetchall()


def topic_seen(
    agent_id: str,
    url: str,
) -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM topics
            WHERE agent_id = ?
            AND url = ?
            LIMIT 1
            """,
            (
                agent_id,
                url,
            ),
        ).fetchone()

        return row is not None


def save_topic(
    topic_key: str,
    agent_id: str,
    title: str,
    url: str,
    source: str,
    discovered_at: str,
    score: float,
    decision: str,
    reason: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO topics(
                topic_key,
                agent_id,
                title,
                url,
                source,
                discovered_at,
                score,
                decision,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_key,
                agent_id,
                title,
                url,
                source,
                discovered_at,
                score,
                decision,
                reason,
            ),
        )


def recent_posts(
    agent_id: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                created_at,
                text,
                rationale,
                sources
            FROM posts
            WHERE agent_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (
                agent_id,
                limit,
            ),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "createdAt": row["created_at"],
            "text": row["text"],
            "rationale": row["rationale"],
            "sources": json.loads(row["sources"]),
        }
        for row in rows
    ]


def save_post(
    post_id: str,
    agent_id: str,
    created_at: str,
    text: str,
    rationale: str,
    sources: list[str],
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO posts(
                id,
                agent_id,
                created_at,
                text,
                rationale,
                sources
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                post_id,
                agent_id,
                created_at,
                text,
                rationale,
                json.dumps(
                    sources,
                    ensure_ascii=False,
                ),
            ),
        )
