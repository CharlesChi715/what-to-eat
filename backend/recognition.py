import os
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

RECOGNITION_PROMPT = """
Identify only edible food objects that are visibly present in this image.

Rules:
- Return raw or cooked food items that can be seen directly.
- Use ordinary ingredient names, such as "tomato" or "chicken breast".
- Ignore plates, bowls, utensils, hands, appliances, packaging, labels, and all
  other non-food objects.
- Do not perform label OCR and do not infer hidden ingredients from a prepared
  dish. Include a component only when it is visually distinguishable.
- If no edible food object is visible, return an empty list.
- Mark certainty as low when the visual identification is ambiguous.
""".strip()


class EdibleItem(BaseModel):
    name: str = Field(description="Concise, generic name of the visible edible item")
    form: str | None = Field(
        default=None,
        description="Visible form when useful, such as whole, sliced, chopped, raw, or cooked",
    )
    certainty: Literal["high", "medium", "low"]


class RecognitionResult(BaseModel):
    edible_items: list[EdibleItem]


class RecognitionNotConfiguredError(RuntimeError):
    pass


async def recognize_edible_items(
    image_bytes: bytes,
    mime_type: str,
) -> tuple[str, RecognitionResult]:
    print(f"Recognizing edible items in image ({len(image_bytes)} bytes, {mime_type})")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RecognitionNotConfiguredError(
            "GEMINI_API_KEY is not configured on the backend."
        )

    print("DEFAULT_GEMINI_MODEL:", DEFAULT_GEMINI_MODEL)
    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    client = genai.Client(api_key=api_key)
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=[
                RECOGNITION_PROMPT,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RecognitionResult,
            ),
        )
    finally:
        await client.aio.aclose()

    print(f"Gemini recognition response: {response!r}")
    if isinstance(response.parsed, RecognitionResult):
        result = response.parsed
    elif response.text:
        result = RecognitionResult.model_validate_json(response.text)
    else:
        raise RuntimeError("Gemini returned no recognition result.")

    return model, result
