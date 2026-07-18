from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, UploadFile
from typing import Any
from fastapi.staticfiles import StaticFiles

REPO_ROOT = Path(__file__).resolve().parent.parent
PHOTOS_DIR = REPO_ROOT / "data" / "photos"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

app = FastAPI()


@app.post("/api/upload")
async def upload_photo(photo: UploadFile) -> dict[str, Any]:
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(photo.filename or "photo.jpg").suffix or ".jpg"
    dest = PHOTOS_DIR / f"{uuid4().hex}{suffix}"
    content = await photo.read()
    dest.write_bytes(content)
    return {"saved": str(dest.relative_to(REPO_ROOT)), "size_kb": round(len(content) / 1024, 1)}


# In development the frontend is served by Vite (npm run dev) and this mount
# does nothing. After `npm run build`, the backend serves the built files itself.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
