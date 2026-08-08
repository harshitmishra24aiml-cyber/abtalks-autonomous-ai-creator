import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


SYSTEM_PROMPT = """
You are an autonomous AI and technology editorial persona.

You must:
- maintain a stable AI/technology identity;
- prefer technically meaningful developments;
- reject shallow hype, duplicates and weakly relevant stories;
- never invent facts, quotes, numbers or sources;
- distinguish known facts from inference;
- write for engineers and technically curious builders;
- avoid generic "AI will change everything" language.

Editorial principle:
"Don't publish because it's new. Publish because it changes what AI builders can do."
"""


def _fallback_judge(topic: dict[str, Any]) -> dict[str, Any]:
    text = f'{topic["title"]} {topic["summary"]}'.lower()

    keywords = [
        "ai", "artificial intelligence", "machine learning", "llm",
        "language model", "model", "agent", "inference", "transformer",
        "hugging face", "robot", "neural", "gpu", "open source",
        "benchmark", "reasoning",
    ]

    relevance = sum(1 for keyword in keywords if keyword in text)
    score = min(10.0, 4.0 + relevance * 0.9)
    publish = score >= 6.0

    reason = (
        "Selected because the candidate has clear relevance to the "
        "persona's AI/technology scope and enough technical signal."
        if publish else
        "Rejected because the candidate does not provide enough strong "
        "AI/technology signal for this persona."
    )

    return {
        "publish": publish,
        "score": round(score, 2),
        "reason": reason,
    }


def _fallback_write(
    topic: dict[str, Any],
    rationale: dict[str, Any],
) -> dict[str, Any]:
    summary = topic["summary"].strip()

    text = (
        f'🔎 {topic["title"]}\n\n'
        f'{summary[:900]}\n\n'
        "NOVA's take: the useful question is not whether this is a "
        "headline-worthy announcement, but whether it changes an engineer's "
        "available choices. The signal worth watching is what this enables "
        "in real AI systems: building, evaluation, inference, deployment, "
        "or developer workflow."
    )

    rationale_text = (
        f'{rationale["reason"]} '
        "It is relevant now because it was discovered from a live "
        "AI/technology information source during the autonomous cycle."
    )

    return {"text": text, "rationale": rationale_text}


class LLM:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "").strip()
        self.client = None

        if self.api_key and self.model and AsyncOpenAI:
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def judge(
        self,
        persona_name: str,
        domain: str,
        topic: dict[str, Any],
        recent_posts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.client:
            return _fallback_judge(topic)

        recent = "\n\n".join(
            post["text"][:500] for post in recent_posts[:5]
        )

        prompt = f"""
Persona name: {persona_name}
Persona domain: {domain}

Candidate:
Title: {topic["title"]}
Summary: {topic["summary"]}
Source: {topic["source"]}
URL: {topic["url"]}

Recent posts:
{recent or "(none)"}

Return JSON only:
{{
  "publish": true or false,
  "score": number from 0 to 10,
  "reason": "short editorial explanation"
}}

Reject duplicates, generic hype, weakly relevant topics and promotional
content with little informational value.

Prefer meaningful technical changes, new capabilities, useful engineering
lessons, significant model/tool releases and research with practical impact.
"""

        try:
            response = await self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
            )
            result = json.loads(response.output_text)

            if not isinstance(result.get("publish"), bool):
                raise ValueError("Invalid publish field")

            return {
                "publish": result["publish"],
                "score": float(result.get("score", 0)),
                "reason": str(result.get("reason", "")),
            }
        except Exception:
            return _fallback_judge(topic)

    async def write(
        self,
        persona_name: str,
        domain: str,
        topic: dict[str, Any],
        judge_result: dict[str, Any],
        recent_posts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.client:
            return _fallback_write(topic, judge_result)

        recent = "\n\n".join(
            post["text"][:500] for post in recent_posts[:5]
        )

        prompt = f"""
Write one original post.

Persona name: {persona_name}
Persona domain: {domain}

Candidate:
Title: {topic["title"]}
Summary: {topic["summary"]}
Source: {topic["source"]}
URL: {topic["url"]}

Editorial decision:
{json.dumps(judge_result, ensure_ascii=False)}

Recent posts:
{recent or "(none)"}

Return JSON only:
{{
  "text": "the post text",
  "rationale": "why the topic was selected and why it is relevant now"
}}

Requirements:
- Maximum 500 words.
- Clear technical voice.
- No invented facts.
- No invented sources.
- Do not copy the candidate verbatim.
- Explain implications instead of only restating the headline.
- Keep the persona recognizable.
"""

        try:
            response = await self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
            )
            result = json.loads(response.output_text)

            if not result.get("text") or not result.get("rationale"):
                raise ValueError("Invalid generated post")

            return {
                "text": str(result["text"]).strip(),
                "rationale": str(result["rationale"]).strip(),
            }
        except Exception:
            return _fallback_write(topic, judge_result)
