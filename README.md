# NOVA — Autonomous AI Creator

An autonomous AI/technology persona for the **Autonomous AI Creator** challenge.

NOVA discovers live AI topics, judges what is worth publishing, writes in a consistent voice, remembers processed topics and published posts, and continues publishing without additional prompts after initialization.

## Challenge requirements covered

- Live topic discovery
- Editorial judgment and intentional rejection
- Consistent AI/technology persona
- Persistent memory
- Autonomous publishing over time
- Publishing rationale and sources
- Required `POST /api/agent/init`
- Required `GET /api/agent/feed`
- Reverse chronological feed
- Previously published posts remain available

## Architecture

```text
POST /api/agent/init
          |
          v
   Agent Registration
          |
          v
   Autonomous Worker
          |
    +-----+-----+------+
    |           |      |
 Discover      Judge  Memory
    |           |      |
    +-----------+------+
          |
   Publish decision
      /        \
    reject    publish
      |          |
   remember    write
                 |
              persist
                 |
                 v
       GET /api/agent/feed
```

## Persona

Recommended persona:

**NOVA — AI Systems Scout**

Editorial principle:

> Don't publish because it's new. Publish because it changes what AI builders can do.

Focus areas include AI agents, models, developer tools, inference, deployment, edge AI, open-source AI and AI infrastructure.

The API still accepts the persona supplied by the evaluator.

---

## Local setup

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

For development, use `CYCLE_MINUTES=1` so you can see autonomous cycles quickly.

---

## API

### Initialize

```http
POST /api/agent/init
Content-Type: application/json
```

Request:

```json
{
  "persona": {
    "name": "NOVA",
    "domain": "AI and Technology"
  }
}
```

Response:

```json
{
  "agentId": "..."
}
```

The evaluator calls this once.

### Feed

```http
GET /api/agent/feed?agentId=...
```

Response:

```json
{
  "posts": [
    {
      "id": "post-id",
      "createdAt": "2026-08-08T10:30:00Z",
      "text": "Post text...",
      "rationale": "Why it was selected and why it is relevant now.",
      "sources": [
        "https://example.com/source"
      ]
    }
  ]
}
```

If no posts exist:

```json
{
  "posts": []
}
```

Posts are newest first.

### Important autonomy property

`GET /api/agent/feed` **does not generate posts**.

The actual flow is:

```text
/init
  -> starts autonomous worker

worker
  -> discovers
  -> judges
  -> rejects or writes
  -> remembers
  -> publishes
  -> repeats

/feed
  -> retrieves persisted posts only
```

This demonstrates operation without additional human prompts.

---

## LLM configuration

Copy `.env.example` to `.env`.

For LLM-powered judging/writing:

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=your_available_model
```

Set `OPENAI_MODEL` to a model available in your API account.

If the key/model is blank, the project uses a deterministic fallback judge/writer so the API and autonomous pipeline can still be smoke-tested.

---

## Deployment

A `Dockerfile` and `render.yaml` are included.

Environment variables:

```text
OPENAI_API_KEY
OPENAI_MODEL
CYCLE_MINUTES
MAX_TOPICS_PER_CYCLE
```

The Docker command uses the platform-provided `PORT`.

For the challenge, use a service that stays running during the observation period. SQLite is intentionally simple for this MVP; the database persists within the running service and prevents repeated topic processing.

---

## GitHub

Upload the contents of this repository to GitHub.

Do **not** upload `.env`. It is excluded by `.gitignore`.

## Structure

```text
autonomous-ai-creator/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── db.py
│   ├── discovery.py
│   ├── llm.py
│   └── main.py
├── data/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── README.md
├── render.yaml
└── requirements.txt
```
