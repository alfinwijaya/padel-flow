# 🎾 PadelFlow - AI-Powered Padel Tournament Management System

**PadelFlow** is an intelligent, full-stack tournament management web application built for Padel players, club organizers, and event hosts. Powered by **Gemma 4** (`google/gemma-4-26b-a4b-it-maas`) via Google Cloud Vertex AI, **Google Agent Development Kit (ADK 2.x)**, and **Cloud Firestore**, PadelFlow automates tournament creation from natural language descriptions, provides real-time venue recommendations, dynamically calculates round-by-round pairings (Americano & Mexicano formats), and tracks live match scores and leaderboards.

---

## 🔥 Highlighted AI-Assisted Features

PadelFlow leverages **Gemma 4** (`google/gemma-4-26b-a4b-it-maas`) on Google Cloud Vertex AI to deliver a truly agentic tournament management experience:

### 1. 🤖 Smart Tournament Generator with Multi-Turn Challenge Loop
* **Natural Language Parsing**: Accepts unstructured prompts such as *"Organize a 12-player Mexicano padel tournament next Saturday at 5 PM at Kelapa Gading with 3 courts."*
* **Multi-Turn Information Validation**: Automatically detects missing mandatory tournament parameters (such as missing venue location or missing player counts) and initiates a **conversational challenge loop** to request missing details directly from the user rather than hallucinating generic or fake venues.
* **Player List Extraction**: Intelligently extracts individual player names from freeform text or comma-separated lists and maps them directly into tournament rosters.

### 2. 📍 AI Venue Finder Engine
* Accepts location queries and court requirements (e.g., *"Find a venue around BSD with at least 4 courts"*).
* Returns structured venue recommendations complete with court capacities, addresses, and facility highlights (indoor/outdoor, LED lighting, player lounges).

### 3. 💬 Interactive Tournament Advisor Chat Agent
* An embedded AI assistant endpoint (`/api/ai/chat`) providing instant answers for rule clarifications (Americano pair rotations vs. Mexicano rank pairings), balance strategy for odd player counts, and match scheduling advice.

---

## 🌟 Core System Features

* **🔄 Americano & Mexicano Pairing Algorithms**:
  * **Americano**: Rotates player pairings so every participant partners with every other player once.
  * **Mexicano**: Dynamically pairs players based on live ranking positions after each round for balanced, high-stakes matches.
* **⚡ Live Broadcast Scoreboard**: Real-time match scoring interface with a point cap limit (Max 21 points per match) and instant win/loss point diff calculations.
* **🏆 Live Leaderboard**: Real-time rankings table tracking total points, wins, losses, point differences (+/-), and completed matches.
* **☁️ Cloud Firestore Persistence**: All tournament, match, and leaderboard states are automatically synchronized with Google Cloud Firestore, ensuring persistent data across sessions and container restarts.
* **🎨 Sports-Tech UI with Dark/Light Themes**: An editorial-grade, ultra-clean web interface with responsive layouts, typography (`Inter` & `Plus Jakarta Sans`), and custom dark/light theme switching.

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
|---|---|
| **AI Model** | **Gemma 4** (`google/gemma-4-26b-a4b-it-maas`) via Vertex AI OpenAPI Endpoint |
| **Backend Framework** | Python 3.12, FastAPI, Google Agent Development Kit (ADK 2.x) |
| **Data Persistence** | Google Cloud Firestore (with local in-memory fallback) |
| **Frontend UI** | Modern HTML5, CSS3 Custom Properties (Dark/Light mode design tokens), ES6+ JavaScript |
| **Cloud Infrastructure** | Google Cloud Run (Private & Secure Container Deployment) |
| **Dependency Tooling** | `uv` package manager |

---

## 🏗️ Architecture & Data Flow

1. **User Prompt**: Organizers describe tournament specifications or ask for venue recommendations via the **AI Studio**.
2. **AI Reasoning**: The prompt is processed by **Gemma 4** (`google/gemma-4-26b-a4b-it-maas`) on Vertex AI. If mandatory details (e.g. venue location) are missing, sets `status: "needs_info"` and triggers a challenge prompt.
3. **Deterministic Pairing Engine**: [`app/padel_logic.py`](app/padel_logic.py) calculates mathematically fair pair rotations or dynamic Mexicano rankings.
4. **Firestore Storage**: Tournament objects and match states are saved to Google Cloud Firestore (`tournaments` collection).
5. **Real-Time UI Update**: Scores, match cards, and live leaderboard tables render instantly on the web frontend.

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) package manager
- Google Cloud Project with Vertex AI & Firestore enabled

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/alfinwijaya/padel-flow.git
cd padel-flow

# Install Google Agents CLI
uv tool install google-agents-cli

# Install project dependencies
agents-cli install
```

### 3. Environment Variables
Create a `.env` file in the root directory (or copy from `.env.example`):
```env
GOOGLE_CLOUD_PROJECT=kodingdeepdive0826-9594
REGION=us-central1
GOOGLE_CLOUD_LOCATION=global
```

### 4. Run Development Server
```bash
uv run python -m uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser and navigate to `http://localhost:8000`.

---

## 🧪 Testing & Quality Assurance

Run the comprehensive unit and integration test suite:
```bash
uv run pytest tests/unit tests/integration
```

---

## ☁️ Deploying to Google Cloud Run

To deploy PadelFlow to Google Cloud Run as a private service:
```bash
agents-cli deploy -d cloud_run --service-name padel-flow --region us-central1 --project kodingdeepdive0826-9594 --no-confirm-project
```

---

## 📜 License

This project is licensed under the MIT License.
