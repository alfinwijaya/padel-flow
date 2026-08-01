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
import re
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
                err_msg = data.get("error", {}).get("message", str(data)) if isinstance(data, dict) else str(data)
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
    """Simple AI Tournament Generator: Extracts parameters and immediately presents complete specification preview."""
    sys_instruction = (
        "You are an AI Tournament Generator for PadelFlow software.\n"
        "Extract tournament parameters from the user's prompt into JSON.\n\n"
        "Fields to extract:\n"
        "- tournament_name: string (e.g. 'PIK Padel Open')\n"
        "- match_type: string ('Americano' or 'Mexicano')\n"
        "- num_players: integer (default 8 if unspecified)\n"
        "- num_courts: integer (default 2 if unspecified)\n"
        "- target_score: integer (max 21, default 21)\n"
        "- date: string (e.g. '2026-08-08')\n"
        "- time: string (e.g. '09:00')\n"
        "- venue: string (e.g. 'PIK Padel Club')\n"
        "- player_names: array of strings\n\n"
        "Return ONLY a valid JSON object with these keys."
    )

    messages = [
        {"role": "system", "content": sys_instruction},
        {"role": "user", "content": user_prompt},
    ]

    prompt_lower = user_prompt.lower()

    # Extract numbers for num_players and num_courts
    found_nums = [int(n) for n in re.findall(r'\b\d+\b', prompt_lower) if 4 <= int(n) <= 128]
    num_players = found_nums[0] if found_nums else 8
    
    court_match = re.search(r'(\d+)\s*courts?', prompt_lower)
    num_courts = int(court_match.group(1)) if court_match else 2

    match_type = "Mexicano" if "mexicano" in prompt_lower else "Americano"

    # Extract venue
    venue = ""
    venue_match = re.search(r'(?:at|venue|club|near|in|around)\s+([A-Za-z0-9\s]+?)(?=\s+(?:with|for|next|tomorrow|\d+|$|\.))', user_prompt, re.IGNORECASE)
    if venue_match:
        venue = venue_match.group(1).strip().title()
    elif "pik" in prompt_lower:
        venue = "PIK Padel Club"
    elif "bsd" in prompt_lower:
        venue = "BSD Padel Center"
    elif "gading" in prompt_lower:
        venue = "Kelapa Gading Padel Center"
    elif "jakarta" in prompt_lower:
        venue = "Jakarta Padel Club"
    else:
        venue = "Padel Club"

    try:
        raw_output = await call_gemma_api(messages, max_tokens=1024, temperature=0.1)
        parsed = _clean_json_response(raw_output)
        if isinstance(parsed, dict):
            if parsed.get("venue"):
                venue = parsed["venue"]
            if parsed.get("num_players") and isinstance(parsed["num_players"], int) and parsed["num_players"] >= 4:
                num_players = parsed["num_players"]
            if parsed.get("num_courts") and isinstance(parsed["num_courts"], int):
                num_courts = parsed["num_courts"]
            if parsed.get("match_type"):
                match_type = parsed["match_type"]
            t_name = parsed.get("tournament_name") or f"{venue} {match_type} Open"
            p_names = parsed.get("player_names") if isinstance(parsed.get("player_names"), list) else []

            return {
                "status": "complete",
                "missing_fields": [],
                "challenge_message": "",
                "tournament_name": t_name,
                "match_type": match_type,
                "num_players": len(p_names) if len(p_names) >= 4 else num_players,
                "num_courts": num_courts,
                "target_score": 21,
                "date": parsed.get("date") or "2026-08-08",
                "time": parsed.get("time") or "09:00",
                "venue": venue,
                "player_names": p_names,
            }
    except Exception as e:
        logger.error(f"Error in simple ai_generate_tournament: {e}")

    # Fail-safe complete response
    return {
        "status": "complete",
        "missing_fields": [],
        "challenge_message": "",
        "tournament_name": f"{venue} {match_type} Open",
        "match_type": match_type,
        "num_players": num_players,
        "num_courts": num_courts,
        "target_score": 21,
        "date": "2026-08-08",
        "time": "09:00",
        "venue": venue,
        "player_names": [],
    }


async def ai_recommend_venues(user_prompt: str) -> list[dict[str, Any]]:
    """Feature 3: Uses Gemma to recommend padel venues based on user location description."""
    sys_instruction = (
        "You are an AI Venue Recommendation assistant for PadelFlow.\n"
        "Given the user's location description and court requirements, recommend 3 realistic padel venues.\n"
        "Provide clean, concise, realistic venue names (e.g., 'Pantai Indah Kapuk Padel Club', 'PIK Padel Arena', 'The Padel Hub PIK').\n"
        "DO NOT repeat user search prompt words like 'find me a venue near' inside the venue names.\n"
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
            # Clean filler phrases if Gemma repeated prompt text
            for v in parsed:
                if isinstance(v, dict) and "venue_name" in v:
                    v_name = v["venue_name"]
                    for filler in ["Find me a venue near", "find me a venue near", "Find a venue around", "find a venue around", "Search venue near", "search venue near"]:
                        v_name = v_name.replace(filler, "").strip()
                    v["venue_name"] = v_name
            return parsed
    except Exception as e:
        logger.error(f"Error parsing Gemma response for venue recommendations: {e}")

    # Fallback clean location extraction
    clean_loc = user_prompt.lower()
    for filler in ["find me a venue near", "find a venue around", "find venue near", "find venue at", "find venues in", "search venue near", "find me a venue", "find a venue", "near", "around", "at "]:
        clean_loc = clean_loc.replace(filler, "")
    clean_loc = clean_loc.strip().title() or "Padel Center"

    return [
        {
            "venue_name": f"{clean_loc} Padel Club",
            "address": f"Jl. Main Boulevard, {clean_loc}",
            "courts": 4,
            "description": "Panoramic outdoor courts with LED lighting and player lounge.",
        },
        {
            "venue_name": f"Padel Arena {clean_loc}",
            "address": f"Sports Complex, {clean_loc}",
            "courts": 6,
            "description": "Climate-controlled indoor facility with pro-grade turf.",
        },
        {
            "venue_name": f"The Padel Hub {clean_loc}",
            "address": f"Avenue 88, {clean_loc}",
            "courts": 4,
            "description": "Modern courts, pro shop, and spectator grandstand.",
        },
    ]
