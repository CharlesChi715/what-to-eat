# What to Eat

A low-cost personal food-inventory and recipe app. Take a photo of food, confirm what it is, track quantities and expiry dates, and get recipe suggestions for what needs using up.

Status: early MVP — currently a photo-upload round trip (browser → backend → disk).

## Repo layout

```
backend/            FastAPI app (Python, managed by uv from the repo root)
frontend/           React + TypeScript + Vite app (managed by npm, inside this folder)
docs/               Planning docs (MVP workflow)
data/               Runtime data: uploaded photos, database (gitignored)
pyproject.toml      Python dependency record (+ uv.lock)
```

## Development (one machine)

Prerequisites: [uv](https://docs.astral.sh/uv/), Node.js 20+.

Two terminals from the repo root:

```bash
# Terminal A — backend on :8000
uv run uvicorn backend.main:app --reload

# Terminal B — frontend dev server on :5173 (proxies /api/* to :8000)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173.

To point the frontend at a backend on another machine (e.g. the PC):

```bash
VITE_API_TARGET=http://192.168.0.12:8000 npm run dev
```

## Backend server (Windows PC, LAN)

```bash
git clone git@github.com:CharlesChi715/what-to-eat.git
cd what-to-eat
uv sync
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` accepts connections from other devices on the LAN. Allow TCP 8000 through Windows Defender Firewall (private networks). If `frontend/dist` exists (after `npm run build`), the backend also serves the built frontend at `/`.
