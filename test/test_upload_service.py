import os
import json
import asyncio
import pytest
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch, call
import time

# ---------------------------------------------------------------------------
# Stubs — must be installed before the module under test is imported
# ---------------------------------------------------------------------------

channels_stub = types.ModuleType("channels")
channels_stub.IMAGE_UPLOAD_REQUESTED = "image_upload_requested"
channels_stub.IMAGE_UPLOADED = "image_uploaded"
sys.modules.setdefault("channels", channels_stub)

redis_stub = types.ModuleType("redis")
redis_asyncio_stub = types.ModuleType("redis.asyncio")
redis_asyncio_stub.Redis = MagicMock(return_value=MagicMock())
redis_stub.Redis = MagicMock(return_value=MagicMock())
redis_stub.asyncio = redis_asyncio_stub
sys.modules.setdefault("redis", redis_stub)
sys.modules.setdefault("redis.asyncio", redis_asyncio_stub)

# ---------------------------------------------------------------------------
# Import module under test
# ---------------------------------------------------------------------------

import importlib.util, pathlib

SOURCE = pathlib.Path(__file__).parent.parent / "src" / "upload_image.py"
spec = importlib.util.spec_from_file_location("upload_service", SOURCE)
upload_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upload_service)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_redis_client():
    mock_r = AsyncMock()
    mock_r.publish = AsyncMock(return_value=1)
    with patch.object(upload_service, "r", mock_r):
        yield mock_r


# ===========================================================================
# send_image_uploaded_message
# ===========================================================================

class TestSendImageUploadedMessage:
    @pytest.mark.asyncio
    async def test_publishes_to_correct_channel(self, mock_redis_client):
        await upload_service.send_image_uploaded_message("img1", "/tmp/img.jpg", 1234567890.0)

        channel = mock_redis_client.publish.call_args[0][0]
        assert channel == channels_stub.IMAGE_UPLOADED

    @pytest.mark.asyncio
    async def test_payload_contains_all_keys(self, mock_redis_client):
        await upload_service.send_image_uploaded_message("img1", "/tmp/img.jpg", 1234567890.0)

        raw = mock_redis_client.publish.call_args[0][1]
        payload = json.loads(raw)

        assert "image_id" in payload
        assert "image_path" in payload
        assert "timestamp" in payload
        assert "status" in payload

    @pytest.mark.asyncio
    async def test_status_is_uploaded(self, mock_redis_client):
        await upload_service.send_image_uploaded_message("img1", "/tmp/img.jpg", 1234567890.0)

        raw = mock_redis_client.publish.call_args[0][1]
        payload = json.loads(raw)

        assert payload["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_payload_values_match_inputs(self, mock_redis_client):
        await upload_service.send_image_uploaded_message("my_id", "/photos/pic.png", 9999.5)

        raw = mock_redis_client.publish.call_args[0][1]
        payload = json.loads(raw)

        assert payload["image_id"] == "my_id"
        assert payload["image_path"] == "/photos/pic.png"
        assert payload["timestamp"] == 9999.5

    @pytest.mark.asyncio
    async def test_payload_is_valid_json(self, mock_redis_client):
        await upload_service.send_image_uploaded_message("img1", "/tmp/img.jpg", 0.0)

        raw = mock_redis_client.publish.call_args[0][1]
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)


# ===========================================================================
# upload_from_input
# ===========================================================================

class TestUploadFromInput:
    def _make_data(self, image_path: str, image_id: str = "test_img", timestamp: float = 1000.0):
        return {"image_id": image_id, "image_path": image_path, "timestamp": timestamp}

    @pytest.mark.asyncio
    async def test_calls_send_message_for_valid_file(self, tmp_path):
        fake = tmp_path / "photo.jpg"
        fake.write_bytes(b"data")

        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(self._make_data(str(fake)))

        mock_send.assert_awaited_once_with("test_img", str(fake), 1000.0)

    @pytest.mark.asyncio
    async def test_rejects_unsupported_extension(self, tmp_path, capsys):
        fake = tmp_path / "doc.pdf"
        fake.write_bytes(b"data")

        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(self._make_data(str(fake)))

        mock_send.assert_not_awaited()
        assert "not a supported image type" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_rejects_missing_file(self, capsys):
        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(self._make_data("/nonexistent/photo.jpg"))

        mock_send.assert_not_awaited()
        assert "file not found" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_accepts_jpg_extension(self, tmp_path):
        fake = tmp_path / "a.jpg"
        fake.write_bytes(b"x")

        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(self._make_data(str(fake)))

        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_accepts_jpeg_extension(self, tmp_path):
        fake = tmp_path / "a.jpeg"
        fake.write_bytes(b"x")

        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(self._make_data(str(fake)))

        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_accepts_png_extension(self, tmp_path):
        fake = tmp_path / "a.png"
        fake.write_bytes(b"x")

        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(self._make_data(str(fake)))

        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_extension_check_is_case_insensitive(self, tmp_path):
        fake = tmp_path / "a.JPG"
        fake.write_bytes(b"x")

        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(self._make_data(str(fake)))

        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_correct_image_id_and_timestamp(self, tmp_path):
        fake = tmp_path / "shot.png"
        fake.write_bytes(b"x")
        data = self._make_data(str(fake), image_id="unique_42", timestamp=5555.5)

        with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
            await upload_service.upload_from_input(data)

        mock_send.assert_awaited_once_with("unique_42", str(fake), 5555.5)


# ===========================================================================
# listen
# ===========================================================================

class TestListen:
    def _make_pubsub(self, messages: list):
        """Build a mock pubsub whose listen() yields the given messages."""
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()

        async def fake_listen():
            for msg in messages:
                yield msg

        mock_pubsub.listen = fake_listen
        return mock_pubsub

    @pytest.mark.asyncio
    async def test_subscribes_to_correct_channel(self, mock_redis_client):
        mock_pubsub = self._make_pubsub([])
        mock_redis_client.pubsub = MagicMock(return_value=mock_pubsub)

        await upload_service.listen()

        mock_pubsub.subscribe.assert_awaited_once_with(channels_stub.IMAGE_UPLOAD_REQUESTED)

    @pytest.mark.asyncio
    async def test_skips_non_message_types(self, mock_redis_client):
        messages = [
            {"type": "subscribe", "data": "1"},
            {"type": "psubscribe", "data": "2"},
        ]
        mock_pubsub = self._make_pubsub(messages)
        mock_redis_client.pubsub = MagicMock(return_value=mock_pubsub)

        with patch.object(upload_service, "upload_from_input", new=AsyncMock()) as mock_upload, \
             patch("asyncio.create_task") as mock_task:
            await upload_service.listen()

        mock_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_task_for_valid_message(self, mock_redis_client, tmp_path):
        fake = tmp_path / "img.jpg"
        fake.write_bytes(b"x")

        payload = json.dumps({
            "image_id": "abc",
            "image_path": str(fake),
            "timestamp": 1000.0
        })
        messages = [{"type": "message", "data": payload}]
        mock_pubsub = self._make_pubsub(messages)
        mock_redis_client.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("asyncio.create_task") as mock_task:
            await upload_service.listen()

        mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_message_without_image_path(self, mock_redis_client):
        payload = json.dumps({"image_id": "abc", "timestamp": 1000.0})
        messages = [{"type": "message", "data": payload}]
        mock_pubsub = self._make_pubsub(messages)
        mock_redis_client.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("asyncio.create_task") as mock_task:
            await upload_service.listen()

        mock_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_multiple_messages(self, mock_redis_client, tmp_path):
        paths = []
        for name in ["a.jpg", "b.png", "c.jpeg"]:
            f = tmp_path / name
            f.write_bytes(b"x")
            paths.append(str(f))

        messages = [
            {"type": "message", "data": json.dumps({"image_id": f"id{i}", "image_path": p, "timestamp": float(i)})}
            for i, p in enumerate(paths)
        ]
        mock_pubsub = self._make_pubsub(messages)
        mock_redis_client.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("asyncio.create_task") as mock_task:
            await upload_service.listen()

        assert mock_task.call_count == 3