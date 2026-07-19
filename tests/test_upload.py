import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import backend.main as backend_main
from backend.recognition import EdibleItem, RecognitionResult


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
    def test_upload_returns_structured_edible_items(self, recognize: AsyncMock) -> None:
        recognize.return_value = (
            "gpt-5.6-sol",
            RecognitionResult(
                edible_items=[
                    EdibleItem(name="tomato", form="whole", certainty="high")
                ]
            ),
        )

        response = self.client.post(
            "/api/upload",
            files={"photo": ("food.jpg", b"fake-image", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["recognition"]["edible_items"][0]["name"], "tomato")
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


if __name__ == "__main__":
    unittest.main()
