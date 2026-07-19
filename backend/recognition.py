import asyncio
import base64
from io import BytesIO
import os

from openai import AsyncOpenAI
from pillow_heif import open_heif

DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"
HEIF_IMAGE_TYPES = {
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
}

RECOGNITION_PROMPT = """
Describe the edible food objects that are visibly present in this image.
""".strip()


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
) -> tuple[str, str, bytes, str]:
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

    # Notes: Uvicorn create a task for each request, where all task share a single event loop. 
    # To prevent the loop get stucked, use AsyncOpenAI here.
    async with AsyncOpenAI(api_key=api_key) as client:
        print(f"Sending image to GPT-5.6 Sol for recognition...")
        response = await client.responses.create(
            model=model,
            reasoning={"effort": "low"},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": RECOGNITION_PROMPT},
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": "high",
                        },
                    ],
                }
            ],
            store=False,
        )
        print(f"Received response.")

    for output in response.output:
        if output.type != "message":
            continue
        for content in output.content:
            if content.type == "refusal":
                raise RuntimeError(f"GPT-5.6 Sol refused the image: {content.refusal}")

    if response.output_text:
        return model, response.output_text.strip(), image_bytes, mime_type

    raise RuntimeError("GPT-5.6 Sol returned no recognition result.")
