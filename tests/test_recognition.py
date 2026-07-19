import base64
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.recognition import (
    RecognitionNotConfiguredError,
    RecognitionResult,
    recognize_edible_items,
)


class FakeAsyncOpenAI:
    init_kwargs: dict[str, str]
    request_kwargs: dict[str, object]

    def __init__(self, **kwargs: str) -> None:
        type(self).init_kwargs = kwargs
        self.responses = SimpleNamespace(parse=self.parse_response)

    async def __aenter__(self) -> "FakeAsyncOpenAI":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def parse_response(self, **kwargs: object) -> SimpleNamespace:
        type(self).request_kwargs = kwargs
        parsed = RecognitionResult.model_validate(
            {
                "edible_items": [
                    {"name": "tomato", "form": "whole", "certainty": "high"}
                ]
            }
        )
        return SimpleNamespace(output_parsed=parsed, output=[], output_text="")


class RecognizeEdibleItemsTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_gpt_5_6_sol_with_inline_image_and_structured_output(self) -> None:
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("backend.recognition.AsyncOpenAI", FakeAsyncOpenAI),
        ):
            model, result = await recognize_edible_items(b"image-bytes", "image/jpeg")

        self.assertEqual(model, "gpt-5.6-sol")
        self.assertEqual(result.edible_items[0].name, "tomato")
        self.assertEqual(
            FakeAsyncOpenAI.init_kwargs,
            {"api_key": "test-key"},
        )
        request = FakeAsyncOpenAI.request_kwargs
        self.assertEqual(request["model"], "gpt-5.6-sol")
        self.assertEqual(request["reasoning"], {"effort": "high"})
        self.assertIs(request["text_format"], RecognitionResult)
        self.assertIs(request["store"], False)
        content = request["input"][0]["content"]
        expected_image = base64.b64encode(b"image-bytes").decode("ascii")
        self.assertEqual(
            content[1]["image_url"],
            f"data:image/jpeg;base64,{expected_image}",
        )
        self.assertEqual(content[1]["detail"], "high")

    async def test_requires_openai_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RecognitionNotConfiguredError,
                "OPENAI_API_KEY",
            ):
                await recognize_edible_items(b"image-bytes", "image/jpeg")


if __name__ == "__main__":
    unittest.main()
