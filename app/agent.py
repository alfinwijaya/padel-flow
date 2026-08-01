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

import asyncio
from google.adk.agents import Agent
from google.adk.apps import App

from app.gemma_model import GemmaLlm, ai_generate_tournament, ai_recommend_venues
from app.padel_logic import (
    create_tournament_obj,
    get_tournament_dashboard,
    get_tournament_store,
    recalculate_leaderboard,
    update_match_score,
)


def create_padel_tournament(
    name: str,
    match_type: str = "Americano",
    num_players: int = 8,
    num_courts: int = 2,
    target_score: int = 21,
    venue: str = "",
) -> str:
    """Creates a new Padel tournament in PadelFlow.

    Args:
        name: The name of the tournament.
        match_type: Type of match ("Americano" or "Mexicano").
        num_players: Number of players participating.
        num_courts: Number of courts available.
        target_score: Winning target score per match.
        venue: Name or area of venue.

    Returns:
        Confirmation string with tournament details and ID.
    """
    m_type = "Mexicano" if "mexicano" in match_type.lower() else "Americano"
    t = create_tournament_obj(
        name=name,
        match_type=m_type,
        num_players=num_players,
        num_courts=num_courts,
        target_score=target_score,
        venue=venue,
    )
    return (
        f"Tournament '{t.name}' (ID: {t.id}) created successfully! "
        f"Type: {t.match_type}, Players: {t.num_players}, Courts: {t.num_courts}, Target Score: {t.target_score}."
    )


def generate_tournament_from_prompt(prompt: str) -> str:
    """Generates a structured tournament setup from a natural language prompt using Gemma model.

    Args:
        prompt: User's natural language request (e.g. "Create an Americano tournament for 16 players in BSD").

    Returns:
        JSON-formatted string of extracted tournament form fields.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import nest_asyncio

        nest_asyncio.apply()
        result = loop.run_until_complete(ai_generate_tournament(prompt))
    else:
        result = asyncio.run(ai_generate_tournament(prompt))

    return str(result)


def find_venues(query: str) -> str:
    """Recommends padel venues based on user location description using Gemma model.

    Args:
        query: User location query (e.g. "Find a venue around Kelapa Gading with 4 courts").

    Returns:
        JSON string of recommended venues.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import nest_asyncio

        nest_asyncio.apply()
        venues = loop.run_until_complete(ai_recommend_venues(query))
    else:
        venues = asyncio.run(ai_recommend_venues(query))

    return str(venues)


def get_leaderboard_summary(tournament_id: str) -> str:
    """Retrieves current live leaderboard rankings for a tournament.

    Args:
        tournament_id: ID of the tournament.

    Returns:
        String summary of rankings.
    """
    store = get_tournament_store()
    if tournament_id not in store:
        return f"Tournament ID {tournament_id} not found."

    t = store[tournament_id]
    recalculate_leaderboard(t)

    lines = [f"Leaderboard for {t.name}:"]
    for p in t.leaderboard:
        lines.append(
            f"#{p.rank} {p.player_name} - {p.total_points} pts ({p.wins}W / {p.losses}L, diff: {p.point_difference:+d})"
        )
    return "\n".join(lines)


root_agent = Agent(
    name="padel_flow_agent",
    model=GemmaLlm(),
    instruction=(
        "You are PadelFlow AI, an intelligent padel tournament management assistant powered by Gemma.\n"
        "You help organizers create Americano and Mexicano padel tournaments, extract tournament parameters "
        "from natural language prompts, recommend venues, track live scores, and monitor leaderboards."
    ),
    tools=[
        create_padel_tournament,
        generate_tournament_from_prompt,
        find_venues,
        get_leaderboard_summary,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
