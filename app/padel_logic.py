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

import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field


class Match(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    round: int
    court: str
    team_a: list[str]  # e.g. ["Player 1", "Player 2"]
    team_b: list[str]  # e.g. ["Player 3", "Player 4"]
    score_a: int = 0
    score_b: int = 0
    status: Literal["Upcoming", "Ongoing", "Finished"] = "Upcoming"
    winner_team: str | None = None  # "Team A", "Team B", "Draw" or None


class PlayerStats(BaseModel):
    rank: int = 1
    player_name: str
    total_points: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    point_difference: int = 0
    matches_played: int = 0


class Tournament(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    match_type: Literal["Americano", "Mexicano"]
    num_players: int
    num_courts: int
    target_score: int = 21
    date: str
    time: str
    venue: str
    players: list[str] = Field(default_factory=list)
    status: Literal["Setup", "In Progress", "Completed"] = "Setup"
    current_round: int = 0
    matches: list[Match] = Field(default_factory=list)
    leaderboard: list[PlayerStats] = Field(default_factory=list)


# In-memory store for tournaments
_TOURNAMENTS_STORE: dict[str, Tournament] = {}


def get_tournament_store() -> dict[str, Tournament]:
    return _TOURNAMENTS_STORE


def create_tournament_obj(
    name: str,
    match_type: Literal["Americano", "Mexicano"],
    num_players: int,
    num_courts: int,
    target_score: int = 21,
    date: str = "",
    time: str = "",
    venue: str = "",
    player_names: list[str] | None = None,
) -> Tournament:
    """Creates a new tournament and initializes players and leaderboard."""
    if not player_names or len(player_names) < num_players:
        players = [f"Player {i+1}" for i in range(num_players)]
    else:
        players = player_names[:num_players]

    leaderboard = [
        PlayerStats(player_name=p, rank=i + 1) for i, p in enumerate(players)
    ]

    t = Tournament(
        name=name,
        match_type=match_type,
        num_players=num_players,
        num_courts=num_courts,
        target_score=target_score,
        date=date,
        time=time,
        venue=venue,
        players=players,
        leaderboard=leaderboard,
    )
    _TOURNAMENTS_STORE[t.id] = t
    return t


def generate_americano_matches(tournament: Tournament) -> list[Match]:
    """Generates all rounds for an Americano tournament using fair partner and court rotation."""
    players = list(tournament.players)
    n = len(players)
    if n % 2 != 0:
        players.append("Bye")
        n += 1

    num_courts = max(1, tournament.num_courts)
    players_per_court = 4
    max_courts_needed = max(1, n // players_per_court)
    courts_to_use = min(num_courts, max_courts_needed)

    # Standard round-robin cyclic permutation schedule
    rounds_count = n - 1 if n > 1 else 1
    all_matches: list[Match] = []

    # Cyclic rotation
    current_players = list(players)
    for r in range(1, rounds_count + 1):
        # Assign players to courts
        for c_idx in range(courts_to_use):
            start_idx = c_idx * 4
            if start_idx + 3 < len(current_players):
                p1 = current_players[start_idx]
                p2 = current_players[start_idx + 1]
                p3 = current_players[start_idx + 2]
                p4 = current_players[start_idx + 3]

                match = Match(
                    round=r,
                    court=f"Court {c_idx + 1}",
                    team_a=[p1, p2],
                    team_b=[p3, p4],
                    status="Upcoming" if r > 1 else "Ongoing",
                )
                all_matches.append(match)

        # Rotate players array for next round (keep first player fixed, rotate rest)
        if len(current_players) > 1:
            current_players = [current_players[0]] + [current_players[-1]] + current_players[1:-1]

    tournament.matches = all_matches
    tournament.current_round = 1
    tournament.status = "In Progress"
    recalculate_leaderboard(tournament)
    return all_matches


def generate_mexicano_round_1(tournament: Tournament) -> list[Match]:
    """Generates Round 1 matches for a Mexicano tournament."""
    players = list(tournament.players)
    n = len(players)
    num_courts = max(1, tournament.num_courts)
    matches: list[Match] = []

    for c in range(num_courts):
        start_idx = c * 4
        if start_idx + 3 < n:
            p1 = players[start_idx]
            p2 = players[start_idx + 1]
            p3 = players[start_idx + 2]
            p4 = players[start_idx + 3]
            match = Match(
                round=1,
                court=f"Court {c + 1}",
                team_a=[p1, p2],
                team_b=[p3, p4],
                status="Ongoing",
            )
            matches.append(match)

    tournament.matches = matches
    tournament.current_round = 1
    tournament.status = "In Progress"
    recalculate_leaderboard(tournament)
    return matches


def generate_mexicano_next_round(tournament: Tournament) -> list[Match]:
    """Generates the next round for a Mexicano tournament based on current leaderboard rankings."""
    recalculate_leaderboard(tournament)
    sorted_players = [stat.player_name for stat in tournament.leaderboard]
    next_round_num = tournament.current_round + 1
    num_courts = max(1, tournament.num_courts)
    new_matches: list[Match] = []

    # Find previous partnerships to avoid repeat partners
    past_partnerships: set[tuple[str, str]] = set()
    for m in tournament.matches:
        if len(m.team_a) == 2:
            p1, p2 = sorted([m.team_a[0], m.team_a[1]])
            past_partnerships.add((p1, p2))
        if len(m.team_b) == 2:
            p1, p2 = sorted([m.team_b[0], m.team_b[1]])
            past_partnerships.add((p1, p2))

    for c in range(num_courts):
        start_idx = c * 4
        if start_idx + 3 < len(sorted_players):
            group = sorted_players[start_idx : start_idx + 4]
            r1, r2, r3, r4 = group[0], group[1], group[2], group[3]

            # Option 1: 1 & 4 vs 2 & 3
            pair1 = tuple(sorted([r1, r4]))
            # Option 2: 1 & 3 vs 2 & 4
            pair2 = tuple(sorted([r1, r3]))

            if pair1 in past_partnerships and pair2 not in past_partnerships:
                team_a, team_b = [r1, r3], [r2, r4]
            else:
                team_a, team_b = [r1, r4], [r2, r3]

            match = Match(
                round=next_round_num,
                court=f"Court {c + 1}",
                team_a=team_a,
                team_b=team_b,
                status="Ongoing",
            )
            new_matches.append(match)

    tournament.matches.extend(new_matches)
    tournament.current_round = next_round_num
    return new_matches


def update_match_score(
    tournament: Tournament,
    match_id: str,
    score_a: int,
    score_b: int,
    force_status: str | None = None,
) -> Match:
    """Updates the score of a match, checks target score condition, and recalculates leaderboard."""
    match_found = None
    for m in tournament.matches:
        if m.id == match_id:
            match_found = m
            break

    if not match_found:
        raise KeyError(f"Match with id {match_id} not found")

    new_a = max(0, score_a)
    new_b = max(0, score_b)

    # Validate that total match score cannot exceed 21 points or target score
    max_allowed = min(21, tournament.target_score) if tournament.target_score > 0 else 21
    if (new_a + new_b) > max_allowed:
        raise ValueError(f"Total match score ({new_a + new_b}) cannot be more than {max_allowed} points.")

    match_found.score_a = new_a
    match_found.score_b = new_b

    if force_status:
        match_found.status = force_status
    else:
        # Check target score or max points
        if (new_a + new_b) == max_allowed or (
            tournament.target_score > 0 and (match_found.score_a >= tournament.target_score or match_found.score_b >= tournament.target_score)
        ):
            match_found.status = "Finished"
        elif match_found.score_a > 0 or match_found.score_b > 0:
            match_found.status = "Ongoing"

    if match_found.status == "Finished":
        if match_found.score_a > match_found.score_b:
            match_found.winner_team = "Team A"
        elif match_found.score_b > match_found.score_a:
            match_found.winner_team = "Team B"
        else:
            match_found.winner_team = "Draw"

    recalculate_leaderboard(tournament)
    check_tournament_completion(tournament)
    return match_found



def recalculate_leaderboard(tournament: Tournament) -> list[PlayerStats]:
    """Recalculates leaderboard rankings based on finished match scores."""
    stats_map: dict[str, dict[str, int]] = {
        p: {
            "total_points": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "points_conceded": 0,
            "matches_played": 0,
        }
        for p in tournament.players
    }

    for m in tournament.matches:
        if m.status == "Finished" or m.score_a > 0 or m.score_b > 0:
            # Team A players
            for p in m.team_a:
                if p in stats_map:
                    stats_map[p]["total_points"] += m.score_a
                    stats_map[p]["points_conceded"] += m.score_b
                    if m.status == "Finished":
                        stats_map[p]["matches_played"] += 1
                        if m.score_a > m.score_b:
                            stats_map[p]["wins"] += 1
                        elif m.score_a < m.score_b:
                            stats_map[p]["losses"] += 1
                        else:
                            stats_map[p]["draws"] += 1

            # Team B players
            for p in m.team_b:
                if p in stats_map:
                    stats_map[p]["total_points"] += m.score_b
                    stats_map[p]["points_conceded"] += m.score_a
                    if m.status == "Finished":
                        stats_map[p]["matches_played"] += 1
                        if m.score_b > m.score_a:
                            stats_map[p]["wins"] += 1
                        elif m.score_b < m.score_a:
                            stats_map[p]["losses"] += 1
                        else:
                            stats_map[p]["draws"] += 1

    # Convert to list and sort
    player_stats_list = []
    for p_name, data in stats_map.items():
        diff = data["total_points"] - data["points_conceded"]
        player_stats_list.append(
            PlayerStats(
                player_name=p_name,
                total_points=data["total_points"],
                wins=data["wins"],
                losses=data["losses"],
                draws=data["draws"],
                point_difference=diff,
                matches_played=data["matches_played"],
            )
        )

    # Sort by total_points DESC, point_difference DESC, wins DESC
    player_stats_list.sort(
        key=lambda x: (x.total_points, x.point_difference, x.wins), reverse=True
    )

    for rank, stat in enumerate(player_stats_list, start=1):
        stat.rank = rank

    tournament.leaderboard = player_stats_list
    return player_stats_list


def check_tournament_completion(tournament: Tournament) -> bool:
    """Checks if all generated matches are finished."""
    if not tournament.matches:
        return False

    all_finished = all(m.status == "Finished" for m in tournament.matches)
    if all_finished:
        tournament.status = "Completed"
    return all_finished


def get_tournament_dashboard(tournament: Tournament) -> dict[str, Any]:
    """Calculates tournament summary stats and progress widgets for the dashboard."""
    total_matches = len(tournament.matches)
    completed_matches = sum(1 for m in tournament.matches if m.status == "Finished")
    remaining_matches = total_matches - completed_matches
    completion_percentage = (
        round((completed_matches / total_matches) * 100, 1) if total_matches > 0 else 0
    )

    current_leader = (
        tournament.leaderboard[0].player_name if tournament.leaderboard else "N/A"
    )

    return {
        "tournament_id": tournament.id,
        "name": tournament.name,
        "match_type": tournament.match_type,
        "num_players": tournament.num_players,
        "num_courts": tournament.num_courts,
        "target_score": tournament.target_score,
        "status": tournament.status,
        "total_matches": total_matches,
        "completed_matches": completed_matches,
        "remaining_matches": remaining_matches,
        "completion_percentage": completion_percentage,
        "current_round": tournament.current_round,
        "current_leader": current_leader,
        "venue": tournament.venue,
        "date": tournament.date,
        "time": tournament.time,
    }
