import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from backend.recognition import (
    RecognitionNotConfiguredError,
    recognize_edible_items,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

PHOTOS_DIR = REPO_ROOT / "data" / "photos"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
# Inline bytes are base64-encoded in transit, so stay below Gemini's 20 MB
# total-request limit with room for the prompt and JSON envelope.
MAX_INLINE_IMAGE_BYTES = 14 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/api/upload")
async def upload_photo(photo: UploadFile) -> dict[str, Any]:
    print(f"Received upload: {photo.filename} ({photo.content_type})")
    mime_type = (photo.content_type or "").lower()
    if mime_type == "image/jpg":
        mime_type = "image/jpeg"
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Upload a JPEG, PNG, WebP, HEIC, or HEIF image.",
        )

    content = await photo.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(content) > MAX_INLINE_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The image is too large. Upload an image smaller than 14 MB.",
        )

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(photo.filename or "photo.jpg").suffix or ".jpg"
    dest = PHOTOS_DIR / f"{uuid4().hex}{suffix}"
    dest.write_bytes(content)

    try:
        model, recognition = await recognize_edible_items(content, mime_type)
    except RecognitionNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Gemini food recognition failed")
        raise HTTPException(
            status_code=502,
            detail="Gemini could not recognize this image. Try again.",
        ) from exc

    print(f"Saved photo to {dest} ({len(content)} bytes)")
    print(f"Recognition result: {recognition}")
    return {
        "saved": str(dest.relative_to(REPO_ROOT)),
        "size_kb": round(len(content) / 1024, 1),
        "recognition": {
            "model": model,
            **recognition.model_dump(),
        },
    }


# In development the frontend is served by Vite (npm run dev) and this mount
# does nothing. After `npm run build`, the backend serves the built files itself.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
