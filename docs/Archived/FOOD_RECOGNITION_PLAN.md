# Local Food-Recognition System

## Summary

Document this specification in docs/FOOD_RECOGNITION_PLAN.md, with a short link and current-status bullet in
SUMMARY.md.

Build an installable web app for all devices, with the Windows 11 PC acting as the private AI and storage server:

Phone photo → PC server → detect items → classify foods → scan barcode/OCR → show editable results → user confirms

The RTX 3060 runs all models through CUDA in WSL2. There are no paid AI calls. Tailscale remote access is added only
after the home-network version works.

## Implementation - draft plan

### Recognition pipeline

- Use YOLO-World-S to locate multiple separated food objects.
- Classify each detected crop with MobileCLIP2-S0 against precomputed embeddings for thousands of generic food
names.

- Return the five strongest candidates and always require confirmation.
- Decode barcodes with ZXing and retrieve branded products and ingredients from Open Food Facts.
- Use an English PP-OCR mobile model for a separate ingredient-label scanning mode.
- Prioritize barcode identity, confirmed personal examples, and then visual classification.

### Duplicate handling and learning

- Match inventory using barcode, canonical food ID, normalized synonyms, and image similarity.
- Offer separate batch, quantity update, or different-food choices for possible duplicates.
- Store original photos with content-hash filenames and metadata in SQLite.
- Record user corrections and add confirmed photos to a personal similarity index.
- Keep quantity and expiry date as user-entered fields.

### Server and client

- Run FastAPI and PyTorch CUDA under Ubuntu WSL2.
- Use FP16, single-job processing, and controlled model loading to stay within 6 GB VRAM.
- Store inventory metadata in SQLite and original images on the PC filesystem.
- Build an installable responsive web client supporting overview photos, barcodes, OCR, editable boxes, top-five
candidates, and manual entry.

- Cache the last inventory snapshot for read-only access while the server is unavailable.
- Start the server automatically when Windows/WSL starts or resumes.

### Interfaces

- POST /api/recognitions: upload an image and recognition mode; return a job ID.
- GET /api/recognitions/{id}: return progress, boxes, barcodes, OCR, candidates, and duplicate warnings.
- POST /api/recognitions/{id}/confirm: submit corrected detections and inventory information.
- Return editable partial results when one recognition stage fails.

## Test Plan

- Verify CUDA access and keep peak GPU use below 5.5 GB.
- Test at least 60 photos covering separated foods, packages, labels, difficult lighting, rotation, and non-food
objects.

- Target 85% detection recall, 80% top-five food accuracy, and 90% ingredient-word recall on clear photos.
- Target five-second median overview scans and eight-second OCR scans.
- Confirm uncertain results are never silently saved.
- Test duplicate batches, corrections, offline caching, and photo retention.
- Test from iPhone, iPad, Windows, M3 iMac, and Intel MacBook.
- Add Tailscale HTTPS access only after home-network acceptance tests pass.

## Assumptions

- Version 1 is for one user.
- The Windows PC is the primary server and is awakened when needed.
- Recognition covers multiple visible, separated foods—not hidden ingredients inside cooked meals.
- Generic foods use visual recognition; branded products use barcodes.
- OCR is English-first.
- Original photos are retained.
- Model licensing must be reassessed before public or commercial distribution.