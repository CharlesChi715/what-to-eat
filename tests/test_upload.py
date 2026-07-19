import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import backend.main as backend_main
from backend.recognition import InvalidImageError


class UploadPhotoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.original_repo_root = backend_main.REPO_ROOT
        self.original_photos_dir = backend_main.PHOTOS_DIR
        backend_main.REPO_ROOT = self.repo_root
        backend_main.PHOTOS_DIR = self.repo_root / "data" / "photos"
        self.client = TestClient(backend_main.app)

    def tearDown(self) -> None:
        backend_main.REPO_ROOT = self.original_repo_root
        backend_main.PHOTOS_DIR = self.original_photos_dir
        self.temp_dir.cleanup()

    @patch("backend.main.recognize_edible_items", new_callable=AsyncMock)
    def test_upload_returns_unstructured_recognition_text(
        self,
        recognize: AsyncMock,
    ) -> None:
        recognize.return_value = (
            "gpt-5.6-sol",
            "I can see a whole tomato.",
            b"fake-image",
            "image/jpeg",
        )

        response = self.client.post(
            "/api/upload",
            files={"photo": ("food.jpg", b"fake-image", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["recognition"]["text"], "I can see a whole tomato.")
        self.assertEqual(body["sent_image"]["mime_type"], "image/jpeg")
        preview = self.client.get(body["sent_image"]["url"])
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.content, b"fake-image")
        self.assertTrue((self.repo_root / body["saved"]).is_file())
        recognize.assert_awaited_once_with(b"fake-image", "image/jpeg")

    @patch("backend.main.recognize_edible_items", new_callable=AsyncMock)
    def test_upload_rejects_non_image_content(self, recognize: AsyncMock) -> None:
        response = self.client.post(
            "/api/upload",
            files={"photo": ("notes.txt", b"not-an-image", "text/plain")},
        )

        self.assertEqual(response.status_code, 415)
        recognize.assert_not_awaited()

    @patch("backend.main.recognize_edible_items", new_callable=AsyncMock)
    def test_upload_accepts_heic_with_generic_browser_mime_type(
        self,
        recognize: AsyncMock,
    ) -> None:
        recognize.return_value = (
            "gpt-5.6-sol",
            "No edible food is visible.",
            b"converted-jpeg",
            "image/jpeg",
        )

        response = self.client.post(
            "/api/upload",
            files={"photo": ("food.HEIC", b"heic-bytes", "application/octet-stream")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["sent_image"]["mime_type"], "image/jpeg")
        self.assertTrue(body["sent_image"]["url"].endswith("-openai.jpg"))
        preview = self.client.get(body["sent_image"]["url"])
        self.assertEqual(preview.content, b"converted-jpeg")
        recognize.assert_awaited_once_with(b"heic-bytes", "image/heic")

    @patch("backend.main.recognize_edible_items", new_callable=AsyncMock)
    def test_upload_reports_invalid_heic_as_bad_request(
        self,
        recognize: AsyncMock,
    ) -> None:
        recognize.side_effect = InvalidImageError(
            "The HEIC or HEIF image could not be decoded."
        )

        response = self.client.post(
            "/api/upload",
            files={"photo": ("broken.heic", b"not-heic", "image/heic")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "The HEIC or HEIF image could not be decoded.",
        )


if __name__ == "__main__":
    unittest.main()
