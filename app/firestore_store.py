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

import logging
import os
from typing import Any

from app.padel_logic import Tournament, create_tournament_obj

logger = logging.getLogger(__name__)

# Fallback in-memory cache
_IN_MEMORY_STORE: dict[str, Tournament] = {}


class FirestoreTournamentStore:
    """Manages tournament data persistence with Google Cloud Firestore and in-memory fallback."""

    def __init__(self, collection_name: str = "tournaments"):
        self.collection_name = collection_name
        self.db = None
        self._enabled = False

        try:
            from google.cloud import firestore

            project_id = (
                os.getenv("GOOGLE_CLOUD_PROJECT")
                or os.getenv("PROJECT_ID")
                or "kodingdeepdive0826-9594"
            )
            self.db = firestore.Client(project=project_id)
            self._enabled = True
            logger.info(f"Firestore initialized successfully for project '{project_id}'.")
        except Exception as e:
            logger.warning(f"Firestore client initialization warning: {e}. Falling back to in-memory store.")
            self._enabled = False

    def save_tournament(self, tournament: Tournament) -> None:
        """Saves or updates a tournament in Firestore and local cache."""
        _IN_MEMORY_STORE[tournament.id] = tournament

        if self._enabled and self.db:
            try:
                data = tournament.model_dump(mode="json")
                doc_ref = self.db.collection(self.collection_name).document(tournament.id)
                doc_ref.set(data)
            except Exception as e:
                logger.error(f"Error persisting tournament {tournament.id} to Firestore: {e}")

    def get_tournament(self, tournament_id: str) -> Tournament | None:
        """Retrieves a tournament by ID from Firestore or local cache."""
        if self._enabled and self.db:
            try:
                doc_ref = self.db.collection(self.collection_name).document(tournament_id)
                snapshot = doc_ref.get()
                if snapshot.exists:
                    data = snapshot.to_dict() or {}
                    tournament = Tournament.model_validate(data)
                    _IN_MEMORY_STORE[tournament.id] = tournament
                    return tournament
            except Exception as e:
                logger.error(f"Error fetching tournament {tournament_id} from Firestore: {e}")

        return _IN_MEMORY_STORE.get(tournament_id)

    def list_tournaments(self) -> list[Tournament]:
        """Lists all tournaments from Firestore or local cache."""
        tournaments_list: list[Tournament] = []

        if self._enabled and self.db:
            try:
                docs = self.db.collection(self.collection_name).stream()
                for doc in docs:
                    data = doc.to_dict() or {}
                    t = Tournament.model_validate(data)
                    tournaments_list.append(t)
                    _IN_MEMORY_STORE[t.id] = t
                if tournaments_list:
                    return tournaments_list
            except Exception as e:
                logger.error(f"Error streaming tournaments from Firestore: {e}")

        return list(_IN_MEMORY_STORE.values())

    def delete_tournament(self, tournament_id: str) -> bool:
        """Deletes a tournament from Firestore and local cache."""
        deleted = False
        if tournament_id in _IN_MEMORY_STORE:
            del _IN_MEMORY_STORE[tournament_id]
            deleted = True

        if self._enabled and self.db:
            try:
                self.db.collection(self.collection_name).document(tournament_id).delete()
                deleted = True
            except Exception as e:
                logger.error(f"Error deleting tournament {tournament_id} from Firestore: {e}")

        return deleted


_STORE_INSTANCE: FirestoreTournamentStore | None = None


def get_firestore_store() -> FirestoreTournamentStore:
    """Returns singleton instance of FirestoreTournamentStore."""
    global _STORE_INSTANCE
    if _STORE_INSTANCE is None:
        _STORE_INSTANCE = FirestoreTournamentStore()
        # Seed default tournament if store is empty
        if not _STORE_INSTANCE.list_tournaments():
            default_t = create_tournament_obj(
                name="BSD Summer Padel Open",
                match_type="Americano",
                num_players=8,
                num_courts=2,
                target_score=21,
                date="2026-08-08",
                time="09:00",
                venue="BSD Padel Center",
            )
            _STORE_INSTANCE.save_tournament(default_t)

    return _STORE_INSTANCE
