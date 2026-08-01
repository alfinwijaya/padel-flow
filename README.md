# 🎾 PadelFlow - AI-Powered Padel Tournament Management System

**PadelFlow** is an intelligent, full-stack tournament management web application built for Padel players, club organizers, and event hosts. Powered by **Gemma 2 27B** via Google Cloud Vertex AI, **Google Agent Development Kit (ADK 2.x)**, and **Cloud Firestore**, PadelFlow automates tournament creation from natural language descriptions, provides real-time venue recommendations, dynamically calculates round-by-round pairings (Americano & Mexicano formats), and tracks live match scores and leaderboards.

---

## 🌟 Key Features

* **✨ Natural Language AI Tournament Generator**: Describe your tournament setup or paste a list of player names in plain English (e.g. *"Create an Americano tournament for 8 players at BSD Padel Center next Saturday"*). PadelFlow validates missing parameters via a multi-turn challenge loop and generates complete tournament schedules.
* **📍 AI Venue Finder**: Discover top recommended padel courts and venue details based on target location and court availability requirements.
* **🔄 Americano & Mexicano Scheduling Engine**:
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
| **AI Models & Backend** | Gemma 2 27B (`gemma-2-27b-it`) via Vertex AI, Google ADK 2.x, FastAPI, Python 3.12 |
| **Data Persistence** | Google Cloud Firestore (with local in-memory fallback) |
| **Frontend UI** | Modern HTML5, CSS3 Custom Properties (Dark/Light mode design tokens), ES6+ JavaScript |
| **Cloud Deployment** | Google Cloud Run (Private & Secure Execution) |
| **Dependency Management** | `uv` package manager |

---

## 🏗️ Architecture & Data Flow

1. **User Prompt**: Organizers describe tournament specifications or ask for venue recommendations via the **AI Studio**.
2. **AI Inference & Challenge Loop**: The request is routed to **Gemma 2 27B** on Vertex AI. If mandatory details (e.g., player count or venue location) are missing, the AI assistant challenges the user to complete the specifications without hallucinating details.
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
git clone https://github.com/your-username/padel-flow.git
cd padel-flow

# Install Google Agents CLI
uv tool install google-agents-cli

# Install project dependencies
agents-cli install
```

### 3. Environment Variables
Create a `.env` file in the root directory (or copy from `.env.example`):
```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
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
agents-cli deploy -d cloud_run --service-name padel-flow --region us-central1 --project your-gcp-project-id --no-confirm-project
```

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.
