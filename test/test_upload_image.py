import json
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
import sys
sys.path.append('../src')
import upload_image as upload_service

@pytest.fixture
def mock_redis(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(upload_service, "r", mock)
    return mock

@pytest.mark.asyncio
async def test_send_message_publishes_correct_payload(mock_redis):
    await upload_service.send_image_uploaded_message("img1", "/tmp/img.jpg", 123.0)

    mock_redis.publish.assert_awaited_once()

    channel, raw = mock_redis.publish.call_args[0]
    payload = json.loads(raw)

    assert channel == upload_service.IMAGE_UPLOADED
    assert payload["image_id"] == "img1"
    assert payload["image_path"] == "/tmp/img.jpg"
    assert payload["timestamp"] == 123.0
    assert payload["status"] == "uploaded"


# ===========================================================================
# upload_from_input
# ===========================================================================

@pytest.mark.asyncio
async def test_upload_valid_file(tmp_path):
    file = tmp_path / "test.jpg"
    file.write_bytes(b"data")

    with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
        await upload_service.upload_from_input({
            "image_id": "1",
            "image_path": str(file),
            "timestamp": 1.0
        })

    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_rejects_invalid_extension(tmp_path):
    file = tmp_path / "file.txt"
    file.write_bytes(b"x")

    with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
        await upload_service.upload_from_input({
            "image_id": "1",
            "image_path": str(file),
            "timestamp": 1.0
        })

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_upload_rejects_missing_file():
    with patch.object(upload_service, "send_image_uploaded_message", new=AsyncMock()) as mock_send:
        await upload_service.upload_from_input({
            "image_id": "1",
            "image_path": "/does/not/exist.jpg",
            "timestamp": 1.0
        })

    mock_send.assert_not_called()

@pytest.mark.asyncio
async def test_listen_triggers_upload(monkeypatch, tmp_path):
    file = tmp_path / "img.jpg"
    file.write_bytes(b"x")

    async def fake_listen():
        yield {
            "type": "message",
            "data": json.dumps({
                "image_id": "1",
                "image_path": str(file),
                "timestamp": 1.0
            })
        }

    mock_pubsub = AsyncMock()
    mock_pubsub.listen = fake_listen
    mock_pubsub.subscribe = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub

    monkeypatch.setattr(upload_service, "r", mock_redis)

    with patch("asyncio.create_task") as mock_task:
        await upload_service.listen()

    mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_listen_ignores_invalid_message(monkeypatch):
    async def fake_listen():
        yield {
            "type": "message",
            "data": json.dumps({"no_image": True})
        }

    mock_pubsub = AsyncMock()
    mock_pubsub.listen = fake_listen
    mock_pubsub.subscribe = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub

    monkeypatch.setattr(upload_service, "r", mock_redis)

    with patch("asyncio.create_task") as mock_task:
        await upload_service.listen()

    mock_task.assert_not_called()