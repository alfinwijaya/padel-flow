# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
from collections.abc import AsyncIterator

import google.auth
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app
from app.app_utils.a2a import attach_a2a_routes

from a2a.server.tasks import InMemoryTaskStore

from google.adk.runners import Runner

from pydantic import BaseModel

from app.app_utils import services
from app.firestore_store import get_firestore_store
from app.gemma_model import (
    ai_generate_tournament,
    ai_recommend_venues,
    call_gemma_api,
)
from app.padel_logic import (
    Tournament,
    create_tournament_obj,
    generate_americano_matches,
    generate_mexicano_next_round,
    generate_mexicano_round_1,
    get_tournament_dashboard,
    recalculate_leaderboard,
    update_match_score,
)


class Feedback(BaseModel):
    score: int
    user_id: str
    session_id: str
    text: str


try:
    _, project_id = google.auth.default()
except Exception:
    project_id = "kodingdeepdive0826-9594"

allow_origins = ["*"]

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    # Seed initial tournament in store if empty
    store = get_firestore_store()
    if not store.list_tournaments():
        sample_t = create_tournament_obj(
            name="BSD Open Americano",
            match_type="Americano",
            num_players=8,
            num_courts=2,
            target_score=21,
            date="2026-08-08",
            time="09:00",
            venue="BSD Padel Center",
        )
        generate_americano_matches(sample_t)
        store.save_tournament(sample_t)

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app_instance.state.runner = runner
    app_instance.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app_instance,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=False,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=True,
    lifespan=lifespan,
)
app.title = "PadelFlow API"
app.description = "API for PadelFlow AI Tournament Management Powered by Gemma & Firestore"

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files for Frontend UI
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
@app.get("/ui")
def read_root():
    """Serves the main PadelFlow frontend application."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "PadelFlow Backend API is running."}


# Pydantic Schemas for Requests
class CreateTournamentRequest(BaseModel):
    name: str
    match_type: str = "Americano"
    num_players: int = 8
    num_courts: int = 2
    target_score: int = 21
    date: str = ""
    time: str = ""
    venue: str = ""
    players: list[str] | None = None


class UpdateScoreRequest(BaseModel):
    score_a: int
    score_b: int
    force_status: str | None = None


class AIPromptRequest(BaseModel):
    prompt: str


class AIChatRequest(BaseModel):
    message: str


# REST Endpoints with Firestore Persistence
@app.get("/api/tournaments")
def list_tournaments() -> list[dict]:
    store = get_firestore_store()
    return [t.model_dump() for t in store.list_tournaments()]


@app.post("/api/tournaments")
def create_tournament(req: CreateTournamentRequest) -> dict:
    store = get_firestore_store()
    m_type = "Mexicano" if "mexicano" in req.match_type.lower() else "Americano"
    t = create_tournament_obj(
        name=req.name,
        match_type=m_type,
        num_players=req.num_players,
        num_courts=req.num_courts,
        target_score=req.target_score,
        date=req.date,
        time=req.time,
        venue=req.venue,
        player_names=req.players,
    )
    store.save_tournament(t)
    return t.model_dump()


@app.get("/api/tournaments/{tournament_id}")
def get_tournament(tournament_id: str) -> dict:
    store = get_firestore_store()
    t = store.get_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return t.model_dump()


@app.put("/api/tournaments/{tournament_id}")
def update_tournament(tournament_id: str, req: CreateTournamentRequest) -> dict:
    store = get_firestore_store()
    t = store.get_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    t.name = req.name
    t.match_type = "Mexicano" if "mexicano" in req.match_type.lower() else "Americano"
    t.num_players = req.num_players
    t.num_courts = req.num_courts
    t.target_score = req.target_score
    t.date = req.date
    t.time = req.time
    t.venue = req.venue
    if req.players:
        t.players = req.players
    store.save_tournament(t)
    return t.model_dump()


@app.delete("/api/tournaments/{tournament_id}")
def delete_tournament(tournament_id: str) -> dict:
    store = get_firestore_store()
    if store.delete_tournament(tournament_id):
        return {"status": "deleted", "id": tournament_id}
    raise HTTPException(status_code=404, detail="Tournament not found")


@app.post("/api/tournaments/{tournament_id}/generate-matches")
def generate_matches(tournament_id: str) -> dict:
    store = get_firestore_store()
    t = store.get_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if t.match_type == "Americano":
        matches = generate_americano_matches(t)
    else:
        matches = generate_mexicano_round_1(t)

    store.save_tournament(t)
    return {"status": "success", "matches_generated": len(matches), "tournament": t.model_dump()}


@app.post("/api/tournaments/{tournament_id}/next-round")
def generate_next_round(tournament_id: str) -> dict:
    store = get_firestore_store()
    t = store.get_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if t.match_type != "Mexicano":
        raise HTTPException(status_code=400, detail="Next round generation is only for Mexicano tournaments.")

    new_matches = generate_mexicano_next_round(t)
    store.save_tournament(t)
    return {"status": "success", "new_matches_count": len(new_matches), "tournament": t.model_dump()}


@app.post("/api/tournaments/{tournament_id}/matches/{match_id}/score")
def update_score(tournament_id: str, match_id: str, req: UpdateScoreRequest) -> dict:
    store = get_firestore_store()
    t = store.get_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    try:
        updated_match = update_match_score(
            tournament=t,
            match_id=match_id,
            score_a=req.score_a,
            score_b=req.score_b,
            force_status=req.force_status,
        )
        store.save_tournament(t)
        return {"status": "success", "match": updated_match.model_dump(), "tournament": t.model_dump()}
    except KeyError:
        raise HTTPException(status_code=404, detail="Match not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/tournaments/{tournament_id}/leaderboard")
def get_leaderboard(tournament_id: str) -> list[dict]:
    store = get_firestore_store()
    t = store.get_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    leaderboard = recalculate_leaderboard(t)
    store.save_tournament(t)
    return [p.model_dump() for p in leaderboard]


@app.get("/api/tournaments/{tournament_id}/dashboard")
def get_dashboard(tournament_id: str) -> dict:
    store = get_firestore_store()
    t = store.get_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return get_tournament_dashboard(t)


# Gemma AI Endpoints
@app.post("/api/ai/generate-tournament")
async def api_ai_generate_tournament(req: AIPromptRequest) -> dict:
    """Uses Gemma to extract tournament parameters from natural language prompt."""
    return await ai_generate_tournament(req.prompt)


@app.post("/api/ai/recommend-venues")
async def api_ai_recommend_venues(req: AIPromptRequest) -> list[dict]:
    """Uses Gemma to generate padel venue recommendations."""
    return await ai_recommend_venues(req.prompt)


@app.post("/api/ai/chat")
async def api_ai_chat(req: AIChatRequest) -> dict:
    """General chat with Gemma model about padel rules and tournament management."""
    messages = [
        {
            "role": "system",
            "content": "You are PadelFlow AI assistant, an expert in Americano and Mexicano padel tournaments.",
        },
        {"role": "user", "content": req.message},
    ]
    reply = await call_gemma_api(messages, max_tokens=1024)
    return {"reply": reply}


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
