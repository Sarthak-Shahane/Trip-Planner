# AI Trip Planner

Trip planner with a **Flask** backend (local SQLite catalog, no external APIs) and a **Next.js** frontend. Describe a trip in plain text and get places, restaurants, hotels, a day-by-day itinerary, and a budget breakdown.

## Prerequisites

- **Python 3.10+** (with `python3` on your PATH, or adjust root `package.json` `dev:api` to use `python` on Windows)
- **Node.js 18+**

## Quick start (one command)

From the **repository root**:

```bash
npm install
npm run setup
npm run dev
```

This starts:

- **API + static files:** [http://127.0.0.1:5000](http://127.0.0.1:5000) — try [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)
- **Website:** [http://localhost:3000](http://localhost:3000)

Open the site, enter something like **“5 days in Paris, budget 2500”**, and submit.

### Manual start (two terminals)

**Terminal 1 — backend**

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 app.py
```

**Terminal 2 — frontend**

```bash
cd frontend
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

## Configuration (optional)

| File | Purpose |
|------|---------|
| `frontend/.env.local` | Copy from `frontend/.env.example`. Set `NEXT_PUBLIC_API_URL` if the API is not at `http://127.0.0.1:5000`. |
| `backend/.env` | Copy from `backend/.env.example`. Set `TRIP_PLANNER_PUBLIC_URL` to the same base URL as the API so image links in JSON match where the browser loads assets. |

If you omit these, defaults assume the API runs at `http://127.0.0.1:5000`.

## Project layout

```
├── backend/           # Flask app, SQLite data, /static placeholders
│   ├── app.py
│   ├── workflow.py
│   ├── trip_database.py
│   └── static/
├── frontend/          # Next.js UI
│   ├── app/page.tsx
│   └── lib/api.ts     # API base URL
└── package.json       # `npm run dev` runs both servers
```

## API

- **GET** `/api/health` — readiness check  
- **POST** `/api/plan_travel` — body: `{ "user_input": "your trip description" }`  
- **GET** `/static/...` — placeholder images used in plan responses  

## License

MIT
