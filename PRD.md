# Product Requirements Document (PRD)

# PadelFlow

### AI-Powered Padel Tournament Management System

---

# 1. Overview

## 1.1 Background

Organizing Americano and Mexicano padel tournaments often requires manual scheduling, scorekeeping, and leaderboard calculations. These tasks become increasingly difficult as the number of players grows.

PadelFlow simplifies tournament management by automating match generation, providing real-time score tracking, maintaining live leaderboards, persisting data to Google Cloud Firestore, and utilizing **Gemma 4** (`google/gemma-4-26b-a4b-it-maas`) via Vertex AI to generate tournaments from natural language, recommend venues, and answer strategy questions.

---

# 2. Objectives

The application aims to:

* Reduce tournament setup time using natural language AI generation.
* Eliminate manual match scheduling via deterministic Americano and Mexicano pairing algorithms.
* Provide real-time broadcast scorekeeping with strict 21-point score caps.
* Automatically calculate live standings, wins, losses, and point differentials (+/-).
* Persist all tournament and leaderboard state in **Google Cloud Firestore**.
* Serve an editorial-grade, ultra-clean sports-tech web interface with Dark/Light theme switching.

---

# 3. Target User

## Tournament Organizer & Club Manager

Responsible for:

* Creating and editing tournaments (manually or via AI).
* Extracting player rosters and specifying venue details.
* Generating matches and rounds.
* Managing live scores with 21-point score caps.
* Monitoring live leaderboards and declaring champions.
* Leveraging AI Studio tools for venue discovery and strategy advice.

---

# 4. Feature Specifications

---

# Feature 1 — Tournament Management & Persistence

## Description

Allows organizers to create, edit, view, and delete tournaments with full persistence backed by **Google Cloud Firestore**.

### Functional Requirements

* Create Tournament (Manual or AI-assisted)
* Edit Tournament parameters (before generating matches)
* Delete Tournament
* View Active Tournament Details
* Persistent state saved in Google Cloud Firestore (`tournaments` collection)

### Tournament Model Schema

| Field             | Type                 | Description |
| ----------------- | -------------------- | ----------- |
| Tournament ID     | String (UUID)        | Unique identifier |
| Tournament Name   | Text                 | Name of event |
| Match Type        | Americano / Mexicano | Rotation format |
| Number of Players | Integer              | Participant count (min 4, step 4) |
| Number of Courts  | Integer              | Active courts available |
| Target Score      | Integer              | Score target (Max 21 pts) |
| Tournament Date   | Date                 | YYYY-MM-DD |
| Tournament Time   | Time                 | HH:MM |
| Venue             | Text                 | Venue location name |
| Player Names      | Array of Strings     | Roster of player names |

---

# Feature 2 — AI Tournament Generator with Multi-Turn Challenge Loop

## Description

Generates complete tournament structures from natural language using **Gemma 4** (`google/gemma-4-26b-a4b-it-maas`) on Vertex AI.

### User Input Example

> "Create an Americano tournament for 8 players: Carlos, Juan, Rafael, Pablo, Fernando, Diego, Lucas, Mateo at BSD Padel Center with 2 courts."

### Multi-Turn Information Validation & Challenge Loop

* **Mandatory Required Details**: Player info/count, match format (Americano/Mexicano), and venue location.
* **Challenge Behavior**: If ANY mandatory detail (such as venue location) is missing from the prompt, Gemma sets `status: "needs_info"`, identifies missing fields, and generates a challenge question asking the user specifically for the missing information.
* **No Hallucinated Venues**: Prevents fake or auto-filled venue names when user input is incomplete.

### Output

Populates the tournament setup card with extracted player rosters, game type, courts, date/time, and target score for user confirmation before launching.

---

# Feature 3 — AI Venue Finder

## Description

Recommends padel clubs and venues based on user location queries using **Gemma 4**.

### User Input Example

> "Find a venue around Kelapa Gading with at least 4 courts."

### Output

Displays structured venue cards containing:

* Venue Name
* Address & Location
* Court Capacity
* Facility Highlights (e.g. indoor/outdoor, LED lighting, coffee lounge)

---

# Feature 4 — AI Tournament Advisor Chat Agent

## Description

An embedded AI assistant (`/api/ai/chat`) providing instant answers to rule questions, pairing balance strategies for odd player numbers, and schedule management advice.

---

# Feature 5 — Match Generation Engine

## Americano Format

Generates the complete tournament schedule immediately:

* Calculates all round pairings.
* Ensures every player partners with every other player once.
* Assigns courts evenly.

## Mexicano Format

Generates Round 1 initially. After each completed round:

1. Calculates current leaderboard rankings.
2. Pairs adjacent ranked players (Rank 1 & 2 vs Rank 3 & 4).
3. Automatically generates the next round.

---

# Feature 6 — Live Match Scoring

## Interface & Rules

* Real-time `+` / `-` point stepper controls.
* **Strict Point Cap Validation**: Total points in a match (`score_a + score_b`) cannot exceed 21 points (or target score).
* Winner detection and match lock once target score is reached.

---

# Feature 7 — Live Leaderboard & Dashboard

* Real-time calculation of player ranks, total points, wins, losses, point differences (+/-), and completed matches.
* Top 3 Podium summary widget on Dashboard.
* Tournament completion progress ring percentage (`completed_matches / total_matches`).

---

# 5. Architecture & Tech Stack

| Layer | Component / Technology |
| ----- | --------------------- |
| **AI Model** | **Gemma 4** (`google/gemma-4-26b-a4b-it-maas`) via Vertex AI |
| **Backend Framework** | Python 3.12, FastAPI, Google ADK (Agent Development Kit 2.x) |
| **Persistence Store** | Google Cloud Firestore |
| **Frontend UI** | Modern HTML5, CSS3 Custom Properties (Dark/Light Mode), ES6+ JavaScript |
| **Deployment** | Google Cloud Run (Private & Secure execution in `us-central1`) |

---

# 6. User Flow

```text
Dashboard / Top Header
    │
    ▼
Select Active Tournament or Open AI Studio
    │
    ├──────────────────────────────┐
    ▼                              ▼
AI Tournament Generator        Manual Form Modal
(Gemma 4 Vertex AI)
    │
    ▼
(If missing venue/players)
Multi-Turn AI Challenge Loop
    │
    ▼
Review & Launch Tournament
    │
    ▼
Save to Cloud Firestore
    │
    ▼
Generate Matches (Americano / Mexicano)
    │
    ▼
Live Match Scoring (Max 21 Pts)
    │
    ▼
Real-Time Leaderboard & Completion Podium
```

---

# 7. Non-Functional Requirements

* **Performance**: Score updates and leaderboard recalculations process instantly (< 200ms).
* **Reliability**: All tournament data persisted in Cloud Firestore.
* **Score Integrity**: Total match points strictly capped at 21.
* **Usability**: Mobile-friendly, dark/light theme switching, editorial sports-tech styling.