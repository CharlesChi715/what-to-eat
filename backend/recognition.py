import asyncio
import base64
from io import BytesIO
import os
from typing import Literal

from openai import AsyncOpenAI
from pillow_heif import open_heif
from pydantic import BaseModel, Field

DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"
HEIF_IMAGE_TYPES = {
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
}

RECOGNITION_PROMPT = """
Identify the edible food objects visibly present in this image.

For each clearly separate food, return an item for user confirmation. Mark it
"certain" only when the visual evidence is strong. For an isolated uncertain
food, put the best guess in `name`, mark it "uncertain", and provide plausible
alternatives. For every returned item, provide a tight bounding box around that
food in a fixed 0..999 coordinate space with the origin at the image's top-left.
Use `x_min`, `y_min`, `x_max`, and `y_max`, and ensure each minimum is smaller
than its corresponding maximum.

When two or more uncertain foods are clustered, touching, overlapping, or
otherwise difficult to distinguish in the same area, do not guess each one.
Instead, add one focused-photo request describing that area and why a closer
photo is needed.

If no edible food is visible, return empty item and follow-up lists and explain
that briefly in `no_food_message`. Otherwise, leave `no_food_message` empty.
""".strip()


class BoundingBox(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class RecognizedItem(BaseModel):
    name: str = Field(description="Best food identification for confirmation.")
    location: str = Field(description="Short description of where it is in the image.")
    certainty: Literal["certain", "uncertain"]
    alternative_guesses: list[str] = Field(
        description="Other plausible names; empty when identification is certain."
    )
    bounding_box: BoundingBox = Field(
        description="Tight food bounds in 0..999 top-left-origin coordinates."
    )


class FollowUpPhotoRequest(BaseModel):
    area: str = Field(description="Short description of the grouped uncertain area.")
    reason: str = Field(description="Why a closer photo is needed.")


class RecognitionResult(BaseModel):
    items: list[RecognizedItem]
    follow_up_photos: list[FollowUpPhotoRequest]
    no_food_message: str


class RecognitionNotConfiguredError(RuntimeError):
    pass


class InvalidImageError(ValueError):
    pass


def _convert_heif_to_jpeg(image_bytes: bytes) -> bytes:
    try:
        with open_heif(image_bytes).to_pillow() as image:
            with image.convert("RGB") as rgb_image:
                output = BytesIO()
                rgb_image.save(output, format="JPEG", quality=90, optimize=True)
                return output.getvalue()
    except (OSError, ValueError) as exc:
        raise InvalidImageError(
            "The HEIC or HEIF image could not be decoded."
        ) from exc


async def recognize_edible_items(
    image_bytes: bytes,
    mime_type: str,
    focus_hint: str | None = None,
) -> tuple[str, RecognitionResult, bytes, str]:
    print(f"Recognizing edible items in image ({len(image_bytes)} bytes, {mime_type})")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RecognitionNotConfiguredError(
            "OPENAI_API_KEY is not configured on the backend."
        )

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if mime_type in HEIF_IMAGE_TYPES:
        print(f"Converting HEIC/HEIF image to JPEG...")
        image_bytes = await asyncio.to_thread(_convert_heif_to_jpeg, image_bytes)
        print(f"Converted")
        mime_type = "image/jpeg"

    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    image_url = f"data:{mime_type};base64,{image_base64}"
    prompt = RECOGNITION_PROMPT
    if focus_hint:
        prompt += (
            "\n\nThis is a closer follow-up photo of the previously ambiguous area "
            f"described as: {focus_hint}. Identify foods in this focused view."
        )

    # Uvicorn handles concurrent requests on one event loop, so use the async client.
    async with AsyncOpenAI(api_key=api_key) as client:
        print("Sending image to GPT-5.6 Sol for recognition...")
        response = await client.responses.parse(
            model=model,
            reasoning={"effort": "low"},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": "original",
                        },
                    ],
                }
            ],
            text_format=RecognitionResult,
            store=False,
        )
        print("Received response.")

    for output in response.output:
        if output.type != "message":
            continue
        for content in output.content:
            if content.type == "refusal":
                raise RuntimeError(f"GPT-5.6 Sol refused the image: {content.refusal}")
            parsed = getattr(content, "parsed", None)
            if parsed is not None:
                return model, parsed, image_bytes, mime_type

    raise RuntimeError("GPT-5.6 Sol returned no structured recognition result.")
