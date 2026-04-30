import os
import json
import time
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
sys.path.append('../src')
import embed_image as image_embedder


@pytest.mark.asyncio
async def test_embed_image_calls_send(monkeypatch):
    """embed_image should call send_image_embedded_message with merged data"""

    mock_send = AsyncMock()
    monkeypatch.setattr(image_embedder, "send_image_embedded_message", mock_send)

    # Patch IMAGE_VECTORS so "123" has data
    fake_vectors = {
        "123": [
            {"object1": {"box": [0, 0, 100, 100], "lat_long": [42.3741, -71.0372]}}
        ]
    }
    monkeypatch.setattr(image_embedder, "IMAGE_VECTORS", fake_vectors)
    monkeypatch.setattr(image_embedder, "add_object_to_index", AsyncMock())
    monkeypatch.setattr(image_embedder, "save_index", AsyncMock())

    input_data = {"image_id": "123", "image_path": "/tmp/test.png"}
    await image_embedder.embed_image(input_data)

    mock_send.assert_awaited_once()

    sent_data = mock_send.call_args[0][0]

    assert sent_data["image_id"] == "123"
    assert sent_data["image_path"] == "/tmp/test.png"
    assert sent_data["num_objects"] == 1       # one object in fake_vectors
    assert "confidence" in sent_data
    assert "timestamp" in sent_data


@pytest.mark.asyncio
async def test_send_image_embedded_message_publishes(monkeypatch):
    """send_image_embedded_message should publish correct payload"""

    mock_publish = AsyncMock()
    monkeypatch.setattr(image_embedder.r, "publish", mock_publish)

    data = {"foo": "bar"}

    await image_embedder.send_image_embedded_message(data)

    mock_publish.assert_awaited_once()

    channel, payload = mock_publish.call_args[0]

    assert channel == image_embedder.IMAGE_EMBEDDED
    assert json.loads(payload) == data


@pytest.mark.asyncio
async def test_listen_triggers_embed(monkeypatch):
    """listen should trigger embed_image when valid message arrives"""

    mock_pubsub = AsyncMock()
    mock_pubsub.listen = AsyncMock()

    # Fake message stream
    async def fake_listen():
        yield {
            "type": "message",
            "data": json.dumps({
                "image_id": "abc",
                "image_path": "/tmp/img.png"
            })
        }
        await asyncio.sleep(0.01)  # allow loop exit

    mock_pubsub.listen = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    monkeypatch.setattr(image_embedder, "r", mock_redis)

    with patch("asyncio.create_task") as mock_task:
        mock_pubsub.listen = fake_listen
        await image_embedder.listen()

    mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_listen_ignores_invalid_messages(monkeypatch):
    """listen should ignore messages without image_path"""

    async def fake_listen():
        yield {
            "type": "message",
            "data": json.dumps({"no_image": True})
        }
        await asyncio.sleep(0.01)

    mock_pubsub = AsyncMock()
    mock_pubsub.listen = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    monkeypatch.setattr(image_embedder, "r", mock_redis)

    mock_embed = AsyncMock()
    monkeypatch.setattr(image_embedder, "embed_image", mock_embed)

    task = asyncio.create_task(image_embedder.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    mock_embed.assert_not_called()