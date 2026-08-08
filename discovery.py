import asyncio
from dataclasses import dataclass

import feedparser


RSS_FEEDS = [
    ("arXiv AI", "https://export.arxiv.org/rss/cs.AI"),
    ("arXiv Machine Learning", "https://export.arxiv.org/rss/cs.LG"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
]


@dataclass
class Topic:
    title: str
    summary: str
    url: str
    source: str
    published_at: str


def _read_feed(name: str, url: str, limit: int) -> list[Topic]:
    parsed = feedparser.parse(url)
    topics: list[Topic] = []

    for entry in parsed.entries[:limit]:
        link = entry.get("link", "").strip()
        title = entry.get("title", "").strip()

        if not link or not title:
            continue

        summary = (
            entry.get("summary", "")
            or entry.get("description", "")
            or ""
        )

        published = (
            entry.get("published", "")
            or entry.get("updated", "")
            or ""
        )

        topics.append(
            Topic(
                title=title,
                summary=summary[:3000],
                url=link,
                source=name,
                published_at=published,
            )
        )

    return topics


async def discover_topics(limit_per_feed: int = 5) -> list[Topic]:
    jobs = [
        asyncio.to_thread(_read_feed, name, url, limit_per_feed)
        for name, url in RSS_FEEDS
    ]

    results = await asyncio.gather(*jobs, return_exceptions=True)

    topics: list[Topic] = []

    for result in results:
        if isinstance(result, Exception):
            continue
        topics.extend(result)

    topics.sort(key=lambda topic: topic.published_at, reverse=True)
    return topics
