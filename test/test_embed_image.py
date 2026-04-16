import json
import pytest
from unittest.mock import AsyncMock, patch

from src import embed_image


@pytest.mark.asyncio
async def test_embed_image_calls_send(monkeypatch):
    """embed_image should call send_image_embedded_message with merged data"""

    mock_send = AsyncMock()
    monkeypatch.setattr(image_embedder, "send_image_embedded_message", mock_send)

    input_data = {
        "image_id": "123",
        "image_path": "/tmp/test.png"
    }

    await image_embedder.embed_image(input_data)

    mock_send.assert_awaited_once()

    sent_data = mock_send.call_args[0][0]

    assert sent_data["image_id"] == "123"
    assert sent_data["image_path"] == "/tmp/test.png"
    assert "embedded_data" in sent_data
    assert sent_data["embedded_data"] == "sample embedded data"


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

    mock_pubsub.listen.side_effect = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub

    monkeypatch.setattr(image_embedder, "r", mock_redis)

    mock_embed = AsyncMock()
    monkeypatch.setattr(image_embedder, "embed_image", mock_embed)

    # Run listener briefly
    task = asyncio.create_task(image_embedder.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    assert mock_embed.called


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
    mock_pubsub.listen.side_effect = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub

    monkeypatch.setattr(image_embedder, "r", mock_redis)

    mock_embed = AsyncMock()
    monkeypatch.setattr(image_embedder, "embed_image", mock_embed)

    task = asyncio.create_task(image_embedder.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    mock_embed.assert_not_called()