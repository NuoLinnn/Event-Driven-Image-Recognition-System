import os
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys

sys.path.append('../src')
import annotate_image as image_annotator


@pytest.mark.asyncio
async def test_annotate_image_calls_send(monkeypatch):
    """annotate_image should call send_image_annotated_message with merged data"""

    mock_send = AsyncMock()
    monkeypatch.setattr(image_annotator, "send_image_annotated_message", mock_send)

    input_data = {
        "image_id": "123",
        "image_path": "/tmp/test.png"
    }

    await image_annotator.annotate_image(input_data)

    mock_send.assert_awaited_once()

    sent_data = mock_send.call_args[0][0]

    assert sent_data["image_id"] == "123"
    assert sent_data["image_path"] == "/tmp/test.png"
    assert "annotated_data" in sent_data
    assert sent_data["annotated_data"] == "sample data"


@pytest.mark.asyncio
async def test_send_image_annotated_message_publishes(monkeypatch):
    """send_image_annotated_message should publish correct payload"""

    mock_publish = AsyncMock()
    monkeypatch.setattr(image_annotator.r, "publish", mock_publish)

    data = {"foo": "bar"}

    await image_annotator.send_image_annotated_message(data)

    mock_publish.assert_awaited_once()

    channel, payload = mock_publish.call_args[0]

    assert channel == image_annotator.IMAGE_ANNOTATED
    assert json.loads(payload) == data


@pytest.mark.asyncio
async def test_listen_triggers_annotate(monkeypatch):
    """listen should trigger annotate_image when valid message arrives"""

    async def fake_listen():
        yield {
            "type": "message",
            "data": json.dumps({
                "image_id": "abc",
                "image_path": "/tmp/img.png"
            })
        }
        await asyncio.sleep(0.01)

    mock_pubsub = AsyncMock()
    mock_pubsub.listen = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    monkeypatch.setattr(image_annotator, "r", mock_redis)

    mock_annotate = AsyncMock()
    monkeypatch.setattr(image_annotator, "annotate_image", mock_annotate)

    task = asyncio.create_task(image_annotator.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    assert mock_annotate.called


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

    monkeypatch.setattr(image_annotator, "r", mock_redis)

    mock_annotate = AsyncMock()
    monkeypatch.setattr(image_annotator, "annotate_image", mock_annotate)

    task = asyncio.create_task(image_annotator.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    mock_annotate.assert_not_called()


@pytest.mark.asyncio
async def test_listen_ignores_non_message(monkeypatch):
    """listen should ignore non-message types"""

    async def fake_listen():
        yield {"type": "subscribe"}
        await asyncio.sleep(0.01)

    mock_pubsub = AsyncMock()
    mock_pubsub.listen = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    monkeypatch.setattr(image_annotator, "r", mock_redis)

    mock_annotate = AsyncMock()
    monkeypatch.setattr(image_annotator, "annotate_image", mock_annotate)

    task = asyncio.create_task(image_annotator.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    mock_annotate.assert_not_called()