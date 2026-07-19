import logging
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from backend.recognition import (
    FoodMarker,
    InvalidImageError,
    RecognitionNotConfiguredError,
    recognize_edible_items,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

PHOTOS_DIR = REPO_ROOT / "data" / "photos"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
# Inline image bytes grow when base64-encoded, so keep request payloads modest.
MAX_INLINE_IMAGE_BYTES = 14 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
}

logger = logging.getLogger(__name__)

app = FastAPI()


def _create_item_overview_thumbnail(
    image_bytes: bytes,
    marker: FoodMarker,
    destination: Path,
) -> None:
    with Image.open(BytesIO(image_bytes)) as source:
        image = ImageOps.exif_transpose(source)
        width, height = image.size

        center_x = max(0, min(999, marker.center_x)) / 999 * (width - 1)
        center_y = max(0, min(999, marker.center_y)) / 999 * (height - 1)
        normalized_radius = max(20, min(500, marker.radius))
        radius = normalized_radius / 999 * min(width, height)
        ring_box = (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        )

        overview = image.convert("RGB")
        ring_width = max(5, round(max(width, height) * 0.012))
        ImageDraw.Draw(overview).ellipse(
            ring_box,
            outline=(230, 35, 35),
            width=ring_width,
        )
        overview.thumbnail((320, 240), Image.Resampling.LANCZOS)
        overview.save(destination, format="JPEG", quality=90, optimize=True)


@app.get("/api/photos/{filename}", response_class=FileResponse)
async def get_photo(filename: str) -> FileResponse:
    photos_dir = PHOTOS_DIR.resolve()
    photo_path = (PHOTOS_DIR / filename).resolve()
    if photo_path.parent != photos_dir or not photo_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(photo_path)


@app.post("/api/upload")
async def upload_photo(
    photo: UploadFile,
    focus_hint: str | None = Form(default=None, max_length=200),
) -> dict[str, Any]:
    print(f"Received upload: {photo.filename} ({photo.content_type})")
    mime_type = (photo.content_type or "").lower()
    suffix = Path(photo.filename or "").suffix.lower()
    if mime_type in {"", "application/octet-stream"} and suffix in {
        ".heic",
        ".heif",
    }:
        mime_type = f"image/{suffix.removeprefix('.')}"
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
    saved_suffix = Path(photo.filename or "photo.jpg").suffix or ".jpg"
    dest = PHOTOS_DIR / f"{uuid4().hex}{saved_suffix}"
    dest.write_bytes(content)

    try:
        if focus_hint:
            recognition_call = recognize_edible_items(
                content,
                mime_type,
                focus_hint=focus_hint,
            )
        else:
            recognition_call = recognize_edible_items(content, mime_type)
        model, recognition_result, sent_image_bytes, sent_mime_type = (
            await recognition_call
        )
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RecognitionNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("GPT-5.6 Sol food recognition failed")
        raise HTTPException(
            status_code=502,
            detail="GPT-5.6 Sol could not recognize this image. Try again.",
        ) from exc

    sent_image_path = dest
    if sent_image_bytes != content or sent_mime_type != mime_type:
        sent_suffix = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }[sent_mime_type]
        sent_image_path = PHOTOS_DIR / f"{dest.stem}-openai{sent_suffix}"
        sent_image_path.write_bytes(sent_image_bytes)

    sent_image_url = f"/api/photos/{sent_image_path.name}"
    recognition_payload = recognition_result.model_dump()
    for index, (item, item_payload) in enumerate(
        zip(recognition_result.items, recognition_payload["items"], strict=True),
        start=1,
    ):
        thumbnail_path = PHOTOS_DIR / f"{dest.stem}-item-{index}.jpg"
        try:
            _create_item_overview_thumbnail(
                sent_image_bytes,
                item.marker,
                thumbnail_path,
            )
        except (OSError, UnidentifiedImageError, ValueError):
            logger.warning(
                "Could not create overview thumbnail for recognized item %s",
                index,
            )
            item_payload["thumbnail_url"] = sent_image_url
        else:
            item_payload["thumbnail_url"] = f"/api/photos/{thumbnail_path.name}"

    print(f"Saved photo to {dest} ({len(content)} bytes)")
    print(f"Recognition result: {recognition_result.model_dump_json()}")
    return {
        "saved": str(dest.relative_to(REPO_ROOT)),
        "size_kb": round(len(content) / 1024, 1),
        "sent_image": {
            "url": sent_image_url,
            "mime_type": sent_mime_type,
            "size_kb": round(len(sent_image_bytes) / 1024, 1),
        },
        "recognition": {
            "model": model,
            **recognition_payload,
        },
    }


# In development the frontend is served by Vite (npm run dev) and this mount
# does nothing. After `npm run build`, the backend serves the built files itself.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
