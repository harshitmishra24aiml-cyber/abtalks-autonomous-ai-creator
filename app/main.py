import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .agent import start_agent, stop_all_agents
from .db import get_active_agents, get_agent, init_db, recent_posts, save_agent


class Persona(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    domain: str = Field(min_length=1, max_length=200)


class InitRequest(BaseModel):
    persona: Persona


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Resume persisted active agents after a process restart.
    for agent in get_active_agents():
        start_agent(
            agent["agent_id"],
            agent["persona_name"],
            agent["domain"],
        )

    yield

    await stop_all_agents()


app = FastAPI(
    title="Autonomous AI Creator",
    version="1.0.0",
    description="Autonomous AI/technology creator for the challenge.",
    lifespan=lifespan,
)


@app.post("/api/agent/init")
async def initialize_agent(request: InitRequest):
    agent_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    save_agent(
        agent_id=agent_id,
        name=request.persona.name,
        domain=request.persona.domain,
        created_at=created_at,
    )

    # From this point, the agent operates without another prompt.
    start_agent(
        agent_id,
        request.persona.name,
        request.persona.domain,
    )

    return {"agentId": agent_id}


@app.get("/api/agent/feed")
async def get_feed(agentId: str = Query(...)):
    if get_agent(agentId) is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown agentId",
        )

    return {"posts": recent_posts(agentId, limit=100)}
