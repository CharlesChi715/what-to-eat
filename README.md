# What to Eat

A low-cost personal food-inventory and recipe app. Take a photo of food, confirm what it is, track quantities and expiry dates, and get recipe suggestions for what needs using up.

Status: early MVP — photo upload and GPT-5.6 Sol natural-language food recognition are wired end to end on the experimental unstructured-output branch.

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

Create an API key in the [OpenAI API dashboard](https://platform.openai.com/api-keys).
Then copy the safe template and put the real key in the new `.env` file:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your-real-key
```

The backend loads the root `.env` automatically. `.env` is ignored by Git;
never put the real key in `.env.example`.

To test another OpenAI model without changing code, set `OPENAI_MODEL` in `.env`.

Two terminals from the repo root:

```bash
# Terminal B — frontend dev server on :5173 (proxies /api/* to :8000)
cd frontend && npm install && npm run dev

# Terminal A — backend on :8000
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:5173.

### Frontend API target

The Vite development server forwards `/api/*` to `http://localhost:8000` by default, so no configuration is needed when frontend and backend run on the same machine.

When the backend runs on another machine, first find that machine's LAN address. For the Windows PC, open PowerShell and run:

```powershell
ipconfig
```

Under the active `Wireless LAN adapter Wi-Fi` or `Ethernet adapter`, copy the `IPv4 Address` (commonly something like `192.168.0.12`). Do not use an address under a `vEthernet (WSL)` adapter or WSL2's internal `172.x.x.x` address.

On the frontend machine, create a machine-local configuration:

```bash
cd frontend
cp .env.example .env.local
```

Edit `.env.local` and replace the placeholder with an address reachable from the frontend machine:

```dotenv
VITE_API_TARGET=http://192.168.0.12:8000
```

Before starting Vite, verify that the frontend machine can reach the backend:

```bash
curl http://192.168.0.12:8000/openapi.json
```

Replace the example address in both commands with the actual backend address. A successful check returns FastAPI's OpenAPI JSON. If it cannot connect, fix the backend binding, WSL2 LAN forwarding, or Windows firewall before troubleshooting Vite.

`.env.local` is ignored by Git, so each developer or device can use its own target. Restart `npm run dev` after changing it; Vite prints the resolved target as `[vite] proxy /api -> ...` during startup.

For a one-time override without creating a file:

```bash
VITE_API_TARGET=http://192.168.0.12:8000 npm run dev
```

## Backend server (Windows PC, LAN)

```bash
git clone git@github.com:CharlesChi715/what-to-eat.git
cd what-to-eat
uv sync
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

This command starts Uvicorn, imports the FastAPI object using `backend.main:app`, listens on host `0.0.0.0` and port `8000`, and enables development reload.

Host `0.0.0.0` makes FastAPI listen on WSL2's IPv4 interfaces, but WSL2's default NAT mode does not expose that port to the LAN by itself. Configure either WSL mirrored networking or a Windows `portproxy` from TCP 8000 to the WSL2 address, and allow TCP 8000 through Windows Defender Firewall on private networks. See [Microsoft's WSL networking guide](https://learn.microsoft.com/windows/wsl/networking#accessing-a-wsl-2-distribution-from-your-local-area-network-lan).

If `frontend/dist` exists (after `npm run build`), the backend also serves the built frontend at `/`.
