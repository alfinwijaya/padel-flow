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

from app.padel_logic import (
    create_tournament_obj,
    generate_americano_matches,
    generate_mexicano_next_round,
    generate_mexicano_round_1,
    get_tournament_dashboard,
    recalculate_leaderboard,
    update_match_score,
)


def test_create_tournament():
    t = create_tournament_obj(
        name="Test Open",
        match_type="Americano",
        num_players=8,
        num_courts=2,
        target_score=21,
    )
    assert t.name == "Test Open"
    assert t.match_type == "Americano"
    assert len(t.players) == 8
    assert len(t.leaderboard) == 8


def test_americano_match_generation():
    t = create_tournament_obj(
        name="Americano Test",
        match_type="Americano",
        num_players=8,
        num_courts=2,
        target_score=21,
    )
    matches = generate_americano_matches(t)

    assert len(matches) > 0
    assert t.current_round == 1
    assert t.status == "In Progress"
    # Check that courts are assigned
    courts = {m.court for m in matches}
    assert "Court 1" in courts


def test_mexicano_match_generation():
    t = create_tournament_obj(
        name="Mexicano Test",
        match_type="Mexicano",
        num_players=8,
        num_courts=2,
        target_score=21,
    )
    r1_matches = generate_mexicano_round_1(t)
    assert len(r1_matches) == 2
    assert t.current_round == 1

    # Simulate finishing round 1 matches
    for m in r1_matches:
        update_match_score(t, m.id, score_a=12, score_b=9)


    # Generate round 2 based on leaderboard
    r2_matches = generate_mexicano_next_round(t)
    assert len(r2_matches) == 2
    assert t.current_round == 2


def test_score_updating_and_leaderboard():
    t = create_tournament_obj(
        name="Scoring Test",
        match_type="Americano",
        num_players=4,
        num_courts=1,
        target_score=21,
    )
    matches = generate_americano_matches(t)
    m = matches[0]

    update_match_score(t, m.id, score_a=12, score_b=9)
    assert m.status == "Finished"
    assert m.winner_team == "Team A"

    # Leaderboard should reflect Team A players having 12 points and 1 Win
    p1 = m.team_a[0]
    p1_stats = next(p for p in t.leaderboard if p.player_name == p1)
    assert p1_stats.total_points == 12
    assert p1_stats.wins == 1
    assert p1_stats.point_difference == 3



def test_dashboard_metrics():
    t = create_tournament_obj(
        name="Dashboard Test",
        match_type="Americano",
        num_players=4,
        num_courts=1,
        target_score=21,
    )
    generate_americano_matches(t)
    dash = get_tournament_dashboard(t)

    assert dash["num_players"] == 4
    assert dash["target_score"] == 21
    assert "completion_percentage" in dash


def test_score_validation_exceeding_21():
    import pytest
    t = create_tournament_obj(
        name="Validation Test",
        match_type="Americano",
        num_players=4,
        num_courts=1,
        target_score=21,
    )
    matches = generate_americano_matches(t)
    m = matches[0]

    with pytest.raises(ValueError, match="Total match score"):
        update_match_score(t, m.id, score_a=15, score_b=10)  # 15 + 10 = 25 > 21

