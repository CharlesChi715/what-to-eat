import asyncio
import base64
from io import BytesIO
import os
from typing import Literal

from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
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
Identify each clearly separate edible food visible in the image.

For each item, return its best name, short location, certainty, alternatives,
and marker. Use "certain" only when evidence is strong. For an isolated
uncertain item, return the best guess with plausible alternatives.

The cyan grid uses 0..999 coordinates with the origin at the top-left. Place
`center_x` and `center_y` directly on visible pixels of the named food. Set
`radius` from 20 to 500, where 100 equals one tenth of the image's shorter side.
Use the smallest circle that encloses the food, and ensure it agrees with
`location`.

If multiple uncertain foods touch or overlap, request one focused follow-up
photo instead of guessing them separately.

If no food is visible, return empty lists and a brief `no_food_message`;
otherwise leave it empty.
""".strip()


class FoodMarker(BaseModel):
    center_x: int = Field(
        description="Horizontal food-center coordinate in the grid's 0..999 space."
    )
    center_y: int = Field(
        description="Vertical food-center coordinate in the grid's 0..999 space."
    )
    radius: int = Field(
        description="Circle radius in 0..999 units relative to the shorter image side."
    )


class RecognizedItem(BaseModel):
    name: str = Field(description="Best food identification for confirmation.")
    location: str = Field(description="Short description of where it is in the image.")
    certainty: Literal["certain", "uncertain"]
    alternative_guesses: list[str] = Field(
        description="Other plausible names; empty when identification is certain."
    )
    marker: FoodMarker = Field(
        description="A circle centered directly on the visible food."
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


def _add_coordinate_grid(image_bytes: bytes) -> bytes:
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGBA")
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise InvalidImageError("The uploaded image could not be decoded.") from exc

    opaque_image = Image.new("RGBA", image.size, (255, 255, 255, 255))
    opaque_image.alpha_composite(image)
    image = opaque_image
    width, height = image.size
    shortest_side = min(width, height)
    line_width = max(1, round(shortest_side * 0.0025))
    font = ImageFont.load_default(size=max(12, round(shortest_side * 0.018)))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    grid_color = (0, 220, 235, 115)
    label_color = (225, 255, 255, 235)
    label_background = (0, 40, 45, 165)

    def draw_label(position: tuple[int, int], label: str) -> None:
        x, y = position
        bounds = draw.textbbox((x, y), label, font=font, stroke_width=1)
        padding = max(2, line_width)
        draw.rounded_rectangle(
            (
                bounds[0] - padding,
                bounds[1] - padding,
                bounds[2] + padding,
                bounds[3] + padding,
            ),
            radius=padding,
            fill=label_background,
        )
        draw.text(
            (x, y),
            label,
            font=font,
            fill=label_color,
            stroke_width=1,
            stroke_fill=(0, 40, 45, 230),
        )

    for step in range(1, 10):
        coordinate = step * 100
        x = round(width * coordinate / 999)
        y = round(height * coordinate / 999)
        draw.line((x, 0, x, height), fill=grid_color, width=line_width)
        draw.line((0, y, width, y), fill=grid_color, width=line_width)
        draw_label((x + line_width * 2, line_width * 2), f"x{coordinate}")
        draw_label((line_width * 2, y + line_width * 2), f"y{coordinate}")

    gridded = Image.alpha_composite(image, overlay).convert("RGB")
    output = BytesIO()
    gridded.save(output, format="JPEG", quality=92, optimize=True)
    return output.getvalue()


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

    gridded_image_bytes = await asyncio.to_thread(_add_coordinate_grid, image_bytes)
    image_base64 = base64.b64encode(gridded_image_bytes).decode("ascii")
    image_url = f"data:image/jpeg;base64,{image_base64}"
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
