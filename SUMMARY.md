# Summary

## Goal for this project

- Build a low-cost food inventory and recipe app. (For now build a MVP only)

## Goal for agent 

- Slowly delivery. Think more, output less. All focus on guide me teach me inspire me.

## My devices
Read it in the path stored in you memory.
- Frontend: web page
- Backend: My PC with WSL2.

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

- Local recognition pipeline is deferred to a later cost-optimization phase, behind the same recognition interface.
- In the later product, the cloud API stays as a permanent fallback (local server unreachable, low-confidence results, model failures).
- In long term, optimize the preference by preference of each diet in long term.
- Barcode scanning (ZXing, client-side) + Open Food Facts stay free; photos go to the paid API only when a barcode doesn't resolve.
- Stack: Python 3.14 + FastAPI backend (uv-managed, repo root); React + TypeScript + Vite frontend (npm, in frontend/); SQLite planned.
- PC runs the backend only (LAN, manual start); iMac develops both; Vite dev server proxies /api to the backend.
- MVP is English-only; machines sync via GitHub (CharlesChi715/what-to-eat).

## Current State / Next Step

- Scaffold done and verified locally: photo upload round-trip (React page → FastAPI → data/photos/) works; frontend builds; backend serves dist.
- Next: Charles runs the two dev servers on iMac and tests in browser; then commit + push, clone on PC, run backend there.
