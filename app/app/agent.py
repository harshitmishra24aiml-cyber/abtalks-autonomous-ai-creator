import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone

from .db import recent_posts, save_post, save_topic, topic_seen
from .discovery import Topic, discover_topics
from .llm import LLM

logger = logging.getLogger(__name__)

TASKS: dict[str, asyncio.Task] = {}
LLM_CLIENT = LLM()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def topic_key(agent_id: str, topic: Topic) -> str:
    return hashlib.sha256(
        f"{agent_id}|{topic.url}".encode()
    ).hexdigest()


async def run_cycle(
    agent_id: str,
    persona_name: str,
    domain: str,
) -> None:
    topics = await discover_topics(
        limit_per_feed=max(
            2,
            int(os.getenv("MAX_TOPICS_PER_CYCLE", "8")),
        )
    )

    if not topics:
        logger.warning("No live topics discovered for %s", agent_id)
        return

    posts = recent_posts(agent_id, limit=10)

    # Gradual publishing: at most one new post per cycle.
    for topic in topics:
        if topic_seen(agent_id, topic.url):
            continue

        candidate = {
            "title": topic.title,
            "summary": topic.summary,
            "url": topic.url,
            "source": topic.source,
        }

        try:
            decision = await LLM_CLIENT.judge(
                persona_name,
                domain,
                candidate,
                posts,
            )
        except Exception:
            logger.exception("Editorial judge failed")
            decision = {
                "publish": False,
                "score": 0,
                "reason": "Editorial judge unavailable.",
            }

        save_topic(
            topic_key=topic_key(agent_id, topic),
            agent_id=agent_id,
            title=topic.title,
            url=topic.url,
            source=topic.source,
            discovered_at=now_iso(),
            score=float(decision.get("score", 0)),
            decision="publish" if decision.get("publish") else "reject",
            reason=str(decision.get("reason", "")),
        )

        if not decision.get("publish"):
            continue

        try:
            generated = await LLM_CLIENT.write(
                persona_name,
                domain,
                candidate,
                decision,
                posts,
            )

            save_post(
                post_id=str(uuid.uuid4()),
                agent_id=agent_id,
                created_at=now_iso(),
                text=generated["text"],
                rationale=generated["rationale"],
                sources=[topic.url],
            )

            logger.info("Published post for agent %s", agent_id)
            return

        except Exception:
            logger.exception("Post generation failed")
            return


async def agent_loop(
    agent_id: str,
    persona_name: str,
    domain: str,
) -> None:
    minutes = max(1, int(os.getenv("CYCLE_MINUTES", "15")))

    while True:
        try:
            await run_cycle(agent_id, persona_name, domain)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Autonomous cycle failed")

        await asyncio.sleep(minutes * 60)


def start_agent(
    agent_id: str,
    persona_name: str,
    domain: str,
) -> None:
    existing = TASKS.get(agent_id)

    if existing and not existing.done():
        return

    TASKS[agent_id] = asyncio.create_task(
        agent_loop(agent_id, persona_name, domain)
    )


async def stop_all_agents() -> None:
    tasks = list(TASKS.values())

    for task in tasks:
        task.cancel()

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    TASKS.clear()
