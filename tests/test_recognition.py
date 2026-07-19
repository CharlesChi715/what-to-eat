import base64
from io import BytesIO
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from pillow_heif import from_pillow

from backend.recognition import (
    InvalidImageError,
    RecognitionNotConfiguredError,
    recognize_edible_items,
)


class FakeAsyncOpenAI:
    init_kwargs: dict[str, str]
    request_kwargs: dict[str, object]

    def __init__(self, **kwargs: str) -> None:
        type(self).init_kwargs = kwargs
        self.responses = SimpleNamespace(create=self.create_response)

    async def __aenter__(self) -> "FakeAsyncOpenAI":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def create_response(self, **kwargs: object) -> SimpleNamespace:
        type(self).request_kwargs = kwargs
        return SimpleNamespace(
            output=[],
            output_text="I can see a whole tomato.",
        )


class RecognizeEdibleItemsTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_gpt_5_6_sol_with_inline_image_and_plain_text_output(self) -> None:
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("backend.recognition.AsyncOpenAI", FakeAsyncOpenAI),
        ):
            model, result, sent_image, sent_mime_type = await recognize_edible_items(
                b"image-bytes",
                "image/jpeg",
            )

        self.assertEqual(model, "gpt-5.6-sol")
        self.assertEqual(result, "I can see a whole tomato.")
        self.assertEqual(sent_image, b"image-bytes")
        self.assertEqual(sent_mime_type, "image/jpeg")
        self.assertEqual(
            FakeAsyncOpenAI.init_kwargs,
            {"api_key": "test-key"},
        )
        request = FakeAsyncOpenAI.request_kwargs
        self.assertEqual(request["model"], "gpt-5.6-sol")
        self.assertEqual(request["reasoning"], {"effort": "high"})
        self.assertNotIn("text_format", request)
        self.assertIs(request["store"], False)
        content = request["input"][0]["content"]
        expected_image = base64.b64encode(b"image-bytes").decode("ascii")
        self.assertEqual(
            content[1]["image_url"],
            f"data:image/jpeg;base64,{expected_image}",
        )
        self.assertEqual(content[1]["detail"], "high")

    async def test_converts_heic_to_jpeg_before_sending_to_openai(self) -> None:
        with Image.new("RGB", (2, 2), color="red") as image:
            heic_buffer = BytesIO()
            from_pillow(image).save(heic_buffer)

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("backend.recognition.AsyncOpenAI", FakeAsyncOpenAI),
        ):
            _, _, sent_image, sent_mime_type = await recognize_edible_items(
                heic_buffer.getvalue(),
                "image/heic",
            )

        request = FakeAsyncOpenAI.request_kwargs
        image_url = request["input"][0]["content"][1]["image_url"]
        prefix, jpeg_base64 = image_url.split(",", maxsplit=1)
        self.assertEqual(prefix, "data:image/jpeg;base64")
        self.assertEqual(sent_mime_type, "image/jpeg")
        self.assertEqual(sent_image, base64.b64decode(jpeg_base64))
        with Image.open(BytesIO(base64.b64decode(jpeg_base64))) as converted:
            self.assertEqual(converted.format, "JPEG")
            self.assertEqual(converted.size, (2, 2))

    async def test_rejects_invalid_heic_data(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with self.assertRaisesRegex(InvalidImageError, "could not be decoded"):
                await recognize_edible_items(b"not-heic", "image/heic")

    async def test_requires_openai_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RecognitionNotConfiguredError,
                "OPENAI_API_KEY",
            ):
                await recognize_edible_items(b"image-bytes", "image/jpeg")


if __name__ == "__main__":
    unittest.main()
