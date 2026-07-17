# Summary

## Goal for this project

- Build a low-cost food inventory and recipe app. 

## Goal for agent 

- Focus on teaching/guiding me. 

## My devices
Read it in the path stored in you memory.

## Requirements

- Store foods, quantities, expiry dates, and ingredients.
- Recognize foods and ingredient labels from photos.
- Show recognition candidates for user confirmation; warn about possible existing/duplicate foods before saving.
- Suggest recipes from:
  - A personal database of recipes the user has tried and liked.
  - Online recipes with strong community ratings/reviews.
- Minimize recurring and infrastructure costs long-term; prefer local/on-device or open-source AI and free data sources (see Decisions for the MVP exception).
- AI may be used selectively to validate or improve the presentation of generated recipes.

## Decisions

- 2026-07-17: MVP uses the OpenAI SDK (paid vision API) for food/label recognition — fastest path to a working app; cost acceptable at single-user volume.
- Local pipeline (docs/FOOD_RECOGNITION_PLAN.md) is deferred to a later cost-optimization phase, behind the same recognition interface.
- In the later product, the cloud API stays as a permanent fallback (local server unreachable, low-confidence results, model failures).
- Barcode scanning (ZXing, client-side) + Open Food Facts stay free; photos go to the paid API only when a barcode doesn't resolve.

## Current State / Next Step

- Planning only; no app code exists yet.
- Next: define MVP scope (stack, hosting, data model) before implementation.
