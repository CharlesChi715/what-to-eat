import base64
import os
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"

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
- Mark all certainty as low in this round.
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
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RecognitionNotConfiguredError(
            "OPENAI_API_KEY is not configured on the backend."
        )

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    image_url = f"data:{mime_type};base64,{image_base64}"

    async with AsyncOpenAI(api_key=api_key) as client:
        response = await client.responses.parse(
            model=model,
            reasoning={"effort": "high"},
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
            text_format=RecognitionResult,
            store=False,
        )

    if isinstance(response.output_parsed, RecognitionResult):
        return model, response.output_parsed

    for output in response.output:
        if output.type != "message":
            continue
        for content in output.content:
            if content.type == "refusal":
                raise RuntimeError(f"GPT-5.6 Sol refused the image: {content.refusal}")

    if response.output_text:
        return model, RecognitionResult.model_validate_json(response.output_text)

    raise RuntimeError("GPT-5.6 Sol returned no recognition result.")
