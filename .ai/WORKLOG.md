# AI Worklog

Newest first. One entry per completed deliverable.

17/07/2026. Set up wireless access from my iMac to files on my Windows PC by exposing a WSL2 Python HTTP server over the local Wi-Fi network:

    I’m not exactly sure if this was the exact step：
    
1. In WSL2, start the server:
   cd ~/temp
   python3 -m http.server 8000

2. In Windows, set the Wi-Fi network to Private which lower restrictions of communication through wifi:
   Settings > Network & internet > Wi-Fi > your network > Network profile > Private

3. Open Windows PowerShell as Administrator.

4. Allow inbound traffic on port 8000:
   New-NetFirewallRule -DisplayName "Python HTTP 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

5. Get the WSL2 IP address in powerShell or ipconfig:
   $wslIp = (wsl hostname -I).Trim().Split()[0]
   $wslIp

6. Forward Windows port 8000 to WSL2:
   netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8000 connectaddress=$wslIp connectport=8000
<!-- # Data transmission flow:
iMac:
→ 192.168.0.12:8000       Windows listenport
→ 172.18.13.22:8000       WSL2 connectport (doesnt have to be same)
→ Uvicorn/FastAPI -->


7. Check the forwarding rule:
   netsh interface portproxy show all

8. From the iMac, open:
   http://192.168.0.12:8000

If it stops working after a WSL restart, recreate step 6 because the WSL IP can change.
## 2026-07-17

- Decided the MVP will use the OpenAI SDK for photo recognition instead of the local YOLO/MobileCLIP/PP-OCR pipeline; the local pipeline is deferred to a later cost-optimization phase.
- Cloud API recognition will remain a permanent fallback path in the developed product (local-first, cloud fallback behind one recognition interface).
- Updated SUMMARY.md with a Decisions section and refreshed the current state.

## 2026-07-17 — Project scaffold (frontend + backend)

- Backend: FastAPI app at backend/main.py with POST /api/upload (saves to data/photos/), serves frontend/dist when built. Deps (fastapi, uvicorn, python-multipart) managed by uv at repo root.
- Frontend: replaced naive HTML page with Vite + React + TypeScript scaffold in frontend/; typed upload component in src/App.tsx; dev proxy /api → backend (VITE_API_TARGET overridable) in vite.config.ts.
- Removed uv-init boilerplate (root main.py) and backend/requirements.txt (pyproject.toml is the single dep record).
- Filled README.md (layout, dev commands, PC deploy steps). Updated SUMMARY.md decisions (stack, PC runs backend only, English-only MVP, online recipes deferred).
- Verified: npm run build passes; curl upload → file lands in data/photos/, JSON reply correct; GET / serves built frontend.
- Next: Charles tests two-terminal dev flow on iMac, then commit/push and clone on PC.

## 2026-07-18 — Gemini edible-object recognition

- Added Gemini 3 Flash image recognition to the existing upload endpoint.
- Restricted structured candidates to directly visible edible objects; OCR and barcode lookup remain separate.
- Added upload validation, frontend error details, setup documentation, and backend tests.
- Verified: backend unit tests pass; frontend production build passes. Live Gemini call awaits `GEMINI_API_KEY`.

## 2026-07-18 — Local Gemini secret configuration

- Added automatic root `.env` loading with `python-dotenv`.
- Added a gitignored local `.env`, a safe `.env.example`, and setup documentation.

## 2026-07-18 — Restore Gemini 3 Flash model

- Diagnosed a 404 caused by the retired `gemini-1.5-flash` model ID and restored `gemini-3-flash-preview`.

## 2026-07-18 — Gemini API billing blocker

- Live Gemini 3 Flash recognition is blocked by:
  `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'Your prepayment credits are depleted. Please go to AI Studio at https://ai.studio/projects to manage your project and billing. Learn more at https://ai.google.dev/gemini-api/docs/billing#prepay. ', 'status': 'RESOURCE_EXHAUSTED'}}`
- Next action: add or restore prepaid credits for the Gemini API project, then retry the upload.

## 2026-07-19

- Replaced Gemini photo recognition with Meta Muse Spark 1.1 via the Meta Model API.
- Removed `google-genai`, added the OpenAI-compatible client, updated configuration/docs, and passed 4 backend tests plus the frontend production build.

## 2026-07-19 — correction

- Switched photo recognition from Muse Spark 1.1 to Kimi K3 (`kimi-k3`) using Moonshot's official API endpoint and key configuration.

## 2026-07-19 — GPT-5.6 Sol

- Switched MVP photo recognition from Kimi K3 to OpenAI GPT-5.6 Sol with native Pydantic structured-output parsing and explicit high-detail image input.

## 2026-07-19 — Responses API

- Migrated photo recognition from Chat Completions to the Responses API while preserving async execution, high reasoning effort, high-detail image input, and Pydantic structured output.
- Kept the one-shot recognition request stateless with `store=False`; all 4 backend tests pass.

## 2026-07-19 — HEIC support

- Added HEIC/HEIF upload support with local JPEG conversion through `pillow-heif` before OpenAI recognition.
- Offloaded decoding to a worker thread so FastAPI's event loop remains responsive; all 8 backend tests pass.
## 2026-07-19 — Unstructured recognition experiment

- Created `experiment/unstructured-output` and changed GPT recognition from schema-parsed data to natural-language `output_text`.
- Updated the upload response and frontend display; all 8 backend tests and the frontend production build pass.
## 2026-07-19 — Sent-image frontend preview

- Added a protected-path photo endpoint and an upload-response URL for the exact normalized bytes sent to OpenAI.
- 2026-07-20: Added structured food confirmation: isolated uncertainty gets a best guess with confirm/correct controls, while grouped uncertainty requests and merges a focused follow-up photo.
- 2026-07-20: Added per-item food thumbnails using GPT-provided normalized bounding boxes and backend-generated image crops, with full-image fallback.
- 2026-07-20: Changed per-item thumbnails to full-scene overview images with each food marked by a red circle.
- 2026-07-20: Removed thumbnail pillarboxing and made each red marker a true circle enclosing the full AI bounding box; tightened the coordinate prompt.
- 2026-07-20: Replaced AI bounding boxes with grid-assisted food center/radius markers while keeping the user-facing photo clean.
- 2026-07-20: Prevented duplicate recognition uploads by disabling the submit button while a request is running.
- The frontend renders the clean recognition photo; all 11 backend tests and the frontend production build/lint pass.
