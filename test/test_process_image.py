import os
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys

sys.path.append('../src')
import process_image as image_processor


@pytest.mark.asyncio
async def test_process_image_calls_send(monkeypatch):
    """process_image should call send_image_processing_requested_message"""

    mock_send = AsyncMock()
    monkeypatch.setattr(image_processor, "send_image_processing_requested_message", mock_send)

    input_data = {
        "image_id": "123",
        "image_path": "/tmp/test.png"
    }

    await image_processor.process_image(input_data)

    mock_send.assert_awaited_once_with(input_data)


@pytest.mark.asyncio
async def test_send_image_processing_requested_message_publishes(monkeypatch):
    """send_image_processing_requested_message should publish correct payload"""

    mock_publish = AsyncMock()
    monkeypatch.setattr(image_processor.r, "publish", mock_publish)

    data = {"foo": "bar"}

    await image_processor.send_image_processing_requested_message(data)

    mock_publish.assert_awaited_once()

    channel, payload = mock_publish.call_args[0]

    assert channel == image_processor.IMAGE_PROCESSING_REQUESTED
    assert json.loads(payload) == data


@pytest.mark.asyncio
async def test_process_embedded_runs(monkeypatch):
    """process_embedded should run without errors"""

    data = {"image_id": "abc"}

    # Just ensure it doesn't crash
    await image_processor.process_embedded(data)


@pytest.mark.asyncio
async def test_process_annotated_runs(monkeypatch):
    """process_annotated should run without errors"""

    data = {"image_id": "xyz"}

    await image_processor.process_annotated(data)


@pytest.mark.asyncio
async def test_listen_triggers_correct_handler(monkeypatch):
    """listen should trigger correct handler based on channel"""

    async def fake_listen():
        yield {
            "type": "message",
            "channel": image_processor.IMAGE_UPLOADED,
            "data": json.dumps({"image_id": "123"})
        }
        await asyncio.sleep(0.01)

    mock_pubsub = AsyncMock()
    mock_pubsub.listen.side_effect = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    monkeypatch.setattr(image_processor, "r", mock_redis)

    mock_handler = AsyncMock()
    monkeypatch.setitem(
        image_processor.CHANNEL_HANDLERS,
        image_processor.IMAGE_UPLOADED,
        mock_handler
    )

    task = asyncio.create_task(image_processor.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    assert mock_handler.called


@pytest.mark.asyncio
async def test_listen_ignores_non_message(monkeypatch):
    """listen should ignore non-message types"""

    async def fake_listen():
        yield {"type": "subscribe"}
        await asyncio.sleep(0.01)

    mock_pubsub = AsyncMock()
    mock_pubsub.listen.side_effect = fake_listen

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    monkeypatch.setattr(image_processor, "r", mock_redis)

    mock_handler = AsyncMock()
    monkeypatch.setitem(
        image_processor.CHANNEL_HANDLERS,
        image_processor.IMAGE_UPLOADED,
        mock_handler
    )

    task = asyncio.create_task(image_processor.listen())
    await asyncio.sleep(0.05)
    task.cancel()

    mock_handler.assert_not_called()