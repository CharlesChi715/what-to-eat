# Summary

## Goal for this project

- Build a low-cost food inventory and recipe app. (For now build a MVP only details in `docs/MVP_WORKFLOW.md`)

## Goal for agent 

- Slowly delivery. Think more, output less. All focus on guide me teach me inspire me.

## My devices
- Frontend: web page
- Backend: My PC with WSL2.
- Communicate through home WIFI router.
For details read `docs/MY_Devices.md`.

## Requirements

- Store foods, quantities, expiry dates, and ingredients.
- Recognize foods and ingredient labels from photos.
- Show recognition candidates for user confirmation; warn about possible existing/duplicate foods before saving.
- Suggest recipes from:
  - A personal database of recipes the user has tried and liked.
  - Online recipes with strong community ratings/reviews (deferred to a post-MVP phase).
- Minimize recurring and infrastructure costs long-term; prefer local/on-device or open-source AI and free data sources (see Decisions for the MVP exception).
- AI may be used selectively to validate or improve the presentation of generated recipes.

## Decisions

- MVP photo recognition uses the OpenAI API (`gpt-5.6-sol`) for visible edible objects; label OCR remains a separate later step.
- Local recognition pipeline is deferred to a later cost-optimization phase, behind the same recognition interface.
- In the later product, the cloud API stays as a permanent fallback (local server unreachable, low-confidence results, model failures).
- In long term, optimize the preference by preference of each diet in long term.
- Barcode scanning (ZXing, client-side) + Open Food Facts stay free; photos go to the paid API only when a barcode doesn't resolve.
- Stack: Python 3.14 + FastAPI backend (uv-managed, repo root); React + TypeScript + Vite frontend (npm, in frontend/); SQLite planned.
- PC runs the backend only (LAN, manual start); iMac develops both; Vite dev server proxies /api to the backend.
- MVP is English-only; machines sync via GitHub (CharlesChi715/what-to-eat).

## Current State / Next Step

- Recognition returns structured items, certainty, alternative guesses, and focused-photo requests.
- The frontend lets users confirm or correct each item and add closer photos for grouped uncertainty.
- Recognition uploads disable their submit button until the request finishes.
- Each item shows an aspect-correct clean scene with a grid-assisted center/radius marker.
- Uploads accept JPEG, PNG, WebP, HEIC, and HEIF; HEIC/HEIF is converted locally to JPEG.
- The frontend shows the clean normalized photo; only the model input receives a coordinate grid.
- Backend loads `OPENAI_API_KEY` from the gitignored root `.env` file.
- Next: add an OpenAI API key to `.env`, run both dev servers, and test recognition with food and non-food photos.
