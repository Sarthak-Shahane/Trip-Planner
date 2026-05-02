# Trip Planner — Backend

Flask API for the trip planner. Handles natural-language trip requests and returns places, restaurants, hotels, itinerary, and budget breakdown.

## Stack

- **Flask** — API server
- **SQLite** — Offline catalog (destinations + places/restaurants/hotels)

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment

Optional `.env` file (see `backend/.env.example`):

- `TRIP_PLANNER_PUBLIC_URL` — base URL used when returning `/static/...` image URLs in JSON

## Run

```bash
python app.py
```

API runs at **http://localhost:5000**. Frontend expects this origin for CORS.

## API

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST   | `/api/plan_travel` | `{ "user_input": "3 days in Paris" }` | Returns full travel plan (places, restaurants, hotels, itinerary, budget_breakdown). |

## Structure

- `app.py` — Flask app and `/api/plan_travel` route
- `workflow.py` — Local workflow and state
- `agents/` — Extraction, Place, Restaurants, Hotels, Itinerary agents
- `trip_database.py` — SQLite schema + seed data (40+ cities) + catalog queries
- `helper.py` / `google_helper.py` — legacy shims (no external calls; local-only)
