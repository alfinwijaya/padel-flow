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

import json
import logging
import os
from typing import Any, AsyncGenerator

import aiohttp
import google.auth
import google.auth.transport.requests
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

logger = logging.getLogger(__name__)

GEMMA_MODEL_NAME = "google/gemma-4-26b-a4b-it-maas"


def _get_auth_and_url() -> tuple[dict[str, str], str]:
    """Gets authentication headers and full endpoint URL for Gemma Vertex AI OpenAPI completion."""
    try:
        creds, default_project = google.auth.default()
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        token = creds.token
    except Exception as e:
        logger.warning(f"Google auth default failed: {e}, attempting fallback.")
        token = ""
        default_project = "kodingdeepdive0826-9594"

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or default_project or "kodingdeepdive0826-9594"
    location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("REGION") or "global"
    endpoint_host = os.getenv("ENDPOINT") or "aiplatform.googleapis.com"

    url = f"https://{endpoint_host}/v1/projects/{project}/locations/{location}/endpoints/openapi/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    return headers, url


async def call_gemma_api(
    messages: list[dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    """Helper function to execute a direct call to the Gemma model via Vertex AI OpenAPI endpoint."""
    headers, url = _get_auth_and_url()
    payload = {
        "model": GEMMA_MODEL_NAME,
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
        "chat_template_kwargs": {"enable_thinking": True},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                err_msg = data.get("error", {}).get("message", str(data))
                raise RuntimeError(f"Gemma API call failed ({resp.status}): {err_msg}")

            if "choices" in data and len(data["choices"]) > 0:
                msg = data["choices"][0]["message"]
                content = msg.get("content")
                if not content and "reasoning_content" in msg:
                    content = msg.get("reasoning_content")
                return content or ""
            raise ValueError(f"Invalid response structure from Gemma: {data}")


class GemmaLlm(BaseLlm):
    """ADK BaseLlm wrapper for Gemma model on Vertex AI OpenAPI endpoint."""

    model: str = GEMMA_MODEL_NAME

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        messages: list[dict[str, str]] = []

        if llm_request.config and llm_request.config.system_instruction:
            sys_inst = llm_request.config.system_instruction
            if isinstance(sys_inst, str):
                messages.append({"role": "system", "content": sys_inst})
            elif hasattr(sys_inst, "parts"):
                sys_text = "\n".join(p.text for p in sys_inst.parts if p.text)
                if sys_text:
                    messages.append({"role": "system", "content": sys_text})

        for c in llm_request.contents:
            role = "assistant" if c.role in ["model", "assistant"] else "user"
            text = "\n".join(p.text for p in c.parts if p.text)
            if text:
                messages.append({"role": role, "content": text})

        if not messages:
            messages.append({"role": "user", "content": "Hello"})

        content_str = await call_gemma_api(messages, max_tokens=2048)

        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=content_str)],
            )
        )


def _clean_json_response(raw_text: str) -> dict[str, Any] | list[Any]:
    """Extracts valid JSON from raw text response, removing code block fences if present."""
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    start_obj = text.find("{")
    start_arr = text.find("[")

    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(text[start_obj:])
        return obj
    elif start_arr != -1:
        decoder = json.JSONDecoder()
        arr, _ = decoder.raw_decode(text[start_arr:])
        return arr

    return json.loads(text)


async def ai_generate_tournament(user_prompt: str) -> dict[str, Any]:
    """Feature 2: Uses Gemma to evaluate completeness, strictly challenge for missing info (venue, player count), and extract tournament parameters."""
    sys_instruction = (
        "You are an AI Tournament Generator for PadelFlow software.\n"
        "Strictly evaluate the user's input to ensure ALL required tournament details are provided by the user.\n"
        "Required mandatory details:\n"
        "1. Player count OR explicit player names\n"
        "2. Venue name or location (Do NOT invent or guess a venue if the user has not mentioned a specific venue name or location!)\n"
        "3. Match format (\"Americano\" or \"Mexicano\")\n\n"
        "Rules:\n"
        "- If ANY of these mandatory details (especially venue or player count) is missing, set status to \"needs_info\".\n"
        "- DO NOT guess or hallucinate a random venue if the user didn't explicitly give one.\n"
        "- If venue is missing, add \"venue\" to missing_fields and ask a challenge question specifically asking for the venue name.\n"
        "- If player count is missing, add \"num_players\" to missing_fields.\n"
        "- ONLY set status to \"complete\" when player info, venue, and format are ALL explicitly specified.\n\n"
        "Return ONLY a valid JSON object with keys:\n"
        "- status: string (\"complete\" or \"needs_info\")\n"
        "- missing_fields: array of strings (e.g. [\"venue\", \"num_players\"])\n"
        "- challenge_message: string (if needs_info, a polite question asking for the specific missing information; empty string if complete)\n"
        "- tournament_name: string\n"
        "- match_type: string (\"Americano\" or \"Mexicano\")\n"
        "- num_players: integer (default 8 if unspecified)\n"
        "- num_courts: integer (default 2 if unspecified)\n"
        "- target_score: integer (max 21, default 21)\n"
        "- date: string\n"
        "- time: string\n"
        "- venue: string (must be empty string \"\" if not provided by user)\n"
        "- player_names: array of strings\n"
        "Do not include explanation or markdown backticks outside JSON."
    )

    messages = [
        {"role": "system", "content": sys_instruction},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_output = await call_gemma_api(messages, max_tokens=1024, temperature=0.1)
        parsed = _clean_json_response(raw_output)
        if isinstance(parsed, dict):
            prompt_lower = user_prompt.lower()
            
            # Check if player count or explicit player list was supplied in user prompt
            player_keywords = ["player", "players", "participant", "participants"]
            has_players_in_prompt = any(kw in prompt_lower for kw in player_keywords) or len(parsed.get("player_names", [])) >= 4
            
            # Check if venue or location was supplied in user prompt
            venue_keywords = ["at ", "venue", "padel", "club", "center", "court", "arena", "location", "bsd", "gading", "jakarta", "serpong"]
            parsed_venue = (parsed.get("venue") or "").strip()
            has_venue_in_prompt = any(kw in prompt_lower for kw in venue_keywords) or (bool(parsed_venue) and parsed_venue.lower() not in ["tbd", "unspecified", ""])

            missing_fields = []
            if not has_venue_in_prompt:
                missing_fields.append("venue")
                parsed["venue"] = ""
            if not has_players_in_prompt:
                missing_fields.append("num_players")

            if missing_fields:
                parsed["status"] = "needs_info"
                parsed["missing_fields"] = missing_fields
                if "venue" in missing_fields and "num_players" in missing_fields:
                    parsed["challenge_message"] = "Please specify the venue location and how many players (or player names) will participate."
                elif "venue" in missing_fields:
                    parsed["challenge_message"] = "Which venue or padel club will the tournament be hosted at?"
                elif "num_players" in missing_fields:
                    parsed["challenge_message"] = "How many players will participate in the tournament, or what are their names?"
            else:
                parsed["status"] = "complete"
                parsed["missing_fields"] = []
                parsed["challenge_message"] = ""

            return parsed
    except Exception as e:
        logger.error(f"Error parsing Gemma response for tournament generation: {e}")

    prompt_lower = user_prompt.lower()
    has_venue = any(kw in prompt_lower for kw in ["at ", "venue", "padel", "club", "center", "court", "arena", "location", "bsd", "gading", "jakarta", "serpong"])
    
    if has_venue:
        return {
            "status": "needs_info",
            "missing_fields": ["num_players"],
            "challenge_message": "How many players will participate in the tournament, or what are their names?",
            "tournament_name": "Jakarta Padel Open",
            "match_type": "Americano",
            "num_players": 8,
            "num_courts": 2,
            "target_score": 21,
            "date": "2026-08-08",
            "time": "09:00",
            "venue": "Jakarta Padel",
            "player_names": [],
        }

    # Fallback missing venue challenge
    return {
        "status": "needs_info",
        "missing_fields": ["venue"],
        "challenge_message": "Please specify the venue name or location where the tournament will take place.",
        "tournament_name": "Padel Tournament",
        "match_type": "Americano",
        "num_players": 8,
        "num_courts": 2,
        "target_score": 21,
        "date": "2026-08-08",
        "time": "09:00",
        "venue": "",
        "player_names": [],
    }


async def ai_recommend_venues(user_prompt: str) -> list[dict[str, Any]]:
    """Feature 3: Uses Gemma to recommend padel venues based on user location description."""
    sys_instruction = (
        "You are an AI Venue Recommendation assistant for PadelFlow.\n"
        "Given the user's location description and court requirements, recommend 3 realistic padel venues.\n"
        "Return ONLY a valid JSON array containing 3 objects with fields:\n"
        "- venue_name: string\n"
        "- address: string\n"
        "- courts: integer (number of courts available)\n"
        "- description: string (short highlight, e.g. indoor courts, pro lights, coffee shop)\n"
        "Do not include any explanation or text outside the JSON array."
    )

    messages = [
        {"role": "system", "content": sys_instruction},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_output = await call_gemma_api(messages, max_tokens=1024, temperature=0.3)
        parsed = _clean_json_response(raw_output)
        if isinstance(parsed, list):
            return parsed
    except Exception as e:
        logger.error(f"Error parsing Gemma response for venue recommendations: {e}")

    clean_location = user_prompt.replace("Find a venue around", "").replace("with at least", "").strip() or "Padel Center"
    return [
        {
            "venue_name": f"{clean_location} Padel Club",
            "address": f"Jl. Main Boulevard, {clean_location}",
            "courts": 4,
            "description": "Panoramic outdoor courts with LED lighting and player lounge.",
        },
        {
            "venue_name": f"Smash Arena {clean_location}",
            "address": f"Sports Complex, {clean_location}",
            "courts": 6,
            "description": "Climate-controlled indoor facility with pro-grade turf.",
        },
        {
            "venue_name": f"The Padel Hub {clean_location}",
            "address": f"Avenue 88, {clean_location}",
            "courts": 4,
            "description": "Modern courts, pro shop, and spectator grandstand.",
        },
    ]
