import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image

import backend.main as backend_main
from backend.recognition import (
    FoodMarker,
    FollowUpPhotoRequest,
    InvalidImageError,
    RecognitionResult,
    RecognizedItem,
)


def _test_jpeg() -> bytes:
    output = BytesIO()
    with Image.new("RGB", (400, 300), color="white") as image:
        image.save(output, format="JPEG")
    return output.getvalue()


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
    def test_upload_returns_structured_items_for_confirmation(
        self,
        recognize: AsyncMock,
    ) -> None:
        image_bytes = _test_jpeg()
        recognize.return_value = (
            "gpt-5.6-sol",
            RecognitionResult(
                items=[
                    RecognizedItem(
                        name="tomato",
                        location="center",
                        certainty="uncertain",
                        alternative_guesses=["red pepper"],
                        marker=FoodMarker(
                            center_x=350,
                            center_y=400,
                            radius=220,
                        ),
                    ),
                    RecognizedItem(
                        name="carrot",
                        location="right",
                        certainty="certain",
                        alternative_guesses=[],
                        marker=FoodMarker(
                            center_x=750,
                            center_y=500,
                            radius=180,
                        ),
                    ),
                ],
                follow_up_photos=[],
                no_food_message="",
            ),
            image_bytes,
            "image/jpeg",
        )

        response = self.client.post(
            "/api/upload",
            files={"photo": ("food.jpg", image_bytes, "image/jpeg")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["recognition"]["items"][0]["name"], "tomato")
        self.assertEqual(body["recognition"]["items"][0]["certainty"], "uncertain")
        self.assertEqual(
            body["recognition"]["items"][0]["alternative_guesses"],
            ["red pepper"],
        )
        self.assertEqual(body["sent_image"]["mime_type"], "image/jpeg")
        preview = self.client.get(body["sent_image"]["url"])
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.content, image_bytes)
        items = body["recognition"]["items"]
        self.assertEqual(items[0]["image_url"], body["sent_image"]["url"])
        self.assertEqual(items[1]["image_url"], body["sent_image"]["url"])
        self.assertTrue(items[0]["image_url"].endswith("/original.jpg"))
        self.assertEqual(items[0]["marker"]["center_x"], 350)
        stored_files = [
            path for path in backend_main.PHOTOS_DIR.rglob("*") if path.is_file()
        ]
        self.assertEqual(stored_files, [self.repo_root / body["saved"]])
        self.assertTrue((self.repo_root / body["saved"]).is_file())
        recognize.assert_awaited_once_with(image_bytes, "image/jpeg")

    @patch("backend.main.recognize_edible_items", new_callable=AsyncMock)
    def test_follow_up_upload_passes_the_group_area_to_recognition(
        self,
        recognize: AsyncMock,
    ) -> None:
        recognize.return_value = (
            "gpt-5.6-sol",
            RecognitionResult(
                items=[],
                follow_up_photos=[
                    FollowUpPhotoRequest(
                        area="back-left corner",
                        reason="Several vegetables overlap.",
                    )
                ],
                no_food_message="",
            ),
            b"fake-image",
            "image/jpeg",
        )

        response = self.client.post(
            "/api/upload",
            files={"photo": ("closer.jpg", b"fake-image", "image/jpeg")},
            data={"focus_hint": "back-left corner"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["recognition"]["follow_up_photos"][0]["area"],
            "back-left corner",
        )
        recognize.assert_awaited_once_with(
            b"fake-image",
            "image/jpeg",
            focus_hint="back-left corner",
        )

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
            RecognitionResult(
                items=[],
                follow_up_photos=[],
                no_food_message="No edible food is visible.",
            ),
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
        self.assertTrue(body["sent_image"]["url"].endswith("/display.jpg"))
        preview = self.client.get(body["sent_image"]["url"])
        self.assertEqual(preview.content, b"converted-jpeg")
        stored_files = [
            path.name
            for path in backend_main.PHOTOS_DIR.rglob("*")
            if path.is_file()
        ]
        self.assertCountEqual(stored_files, ["original.heic", "display.jpg"])
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
        self.assertFalse(backend_main.PHOTOS_DIR.exists())

    def test_photo_route_rejects_parent_directory_traversal(self) -> None:
        outside_photo = self.repo_root / "private.jpg"
        outside_photo.write_bytes(b"not-public")

        response = self.client.get("/api/photos/%2E%2E%2Fprivate.jpg")

        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response.content, b"not-public")


if __name__ == "__main__":
    unittest.main()
