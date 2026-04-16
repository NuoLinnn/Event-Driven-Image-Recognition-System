import os
import json
import time
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src import cli_service

@pytest.fixture
def mock_redis(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(cli_service, "r", mock)
    return mock

def test_pick_image_file_returns_path():
    with patch("tkinter.Tk") as mock_tk, \
         patch("tkinter.filedialog.askopenfilename", return_value="/tmp/img.jpg"):

        mock_root = MagicMock()
        mock_tk.return_value = mock_root

        result = cli_service.pick_image_file()

    assert result == "/tmp/img.jpg"
    mock_root.withdraw.assert_called_once()
    mock_root.destroy.assert_called_once()


def test_pick_image_file_returns_none():
    with patch("tkinter.Tk"), \
         patch("tkinter.filedialog.askopenfilename", return_value=""):

        result = cli_service.pick_image_file()

    assert result is None

@pytest.mark.asyncio
async def test_pick_image_file_async():
    with patch.object(cli_service, "pick_image_file", return_value="/tmp/test.png") as mock_fn:
        result = await cli_service.pick_image_file_async()

    assert result == "/tmp/test.png"
    mock_fn.assert_called_once()


@pytest.mark.asyncio
async def test_send_upload_requested_message(mock_redis):
    await cli_service.send_image_upload_requested_message("/tmp/photo.jpg")

    mock_redis.publish.assert_awaited_once()

    channel, raw = mock_redis.publish.call_args[0]
    payload = json.loads(raw)

    assert channel == cli_service.IMAGE_UPLOAD_REQUESTED
    assert payload["image_id"] == "photo"
    assert os.path.isabs(payload["image_path"])
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_cli_upload_flow_success(tmp_path):
    file = tmp_path / "img.jpg"
    file.write_bytes(b"x")

    with patch("asyncio.get_event_loop") as mock_loop_fn:
        mock_loop = MagicMock()
        mock_loop_fn.return_value = mock_loop

        mock_loop.run_in_executor = AsyncMock(
            side_effect=["upload an image", str(file)]
        )

        with patch.object(cli_service, "send_image_upload_requested_message", new=AsyncMock()) as mock_send:
            await cli_service.get_cli_command()

    mock_send.assert_awaited_once_with(str(file))


@pytest.mark.asyncio
async def test_cli_upload_missing_file(capsys):
    with patch("asyncio.get_event_loop") as mock_loop_fn:
        mock_loop = MagicMock()
        mock_loop_fn.return_value = mock_loop

        mock_loop.run_in_executor = AsyncMock(
            side_effect=["upload an image", "/bad/path.jpg"]
        )

        await cli_service.get_cli_command()

    assert "not found" in capsys.readouterr().out.lower()


@pytest.mark.asyncio
async def test_cli_no_file_selected(capsys):
    with patch("asyncio.get_event_loop") as mock_loop_fn:
        mock_loop = MagicMock()
        mock_loop_fn.return_value = mock_loop

        mock_loop.run_in_executor = AsyncMock(
            side_effect=["upload an image", None]
        )

        await cli_service.get_cli_command()

    assert "no file selected" in capsys.readouterr().out.lower()


@pytest.mark.asyncio
async def test_cli_query_branch(capsys):
    with patch("asyncio.get_event_loop") as mock_loop_fn:
        mock_loop = MagicMock()
        mock_loop_fn.return_value = mock_loop

        mock_loop.run_in_executor = AsyncMock(
            return_value="query a topic"
        )

        await cli_service.get_cli_command()

    assert "querying topic" in capsys.readouterr().out.lower()


@pytest.mark.asyncio
async def test_cli_unknown_command():
    with patch("asyncio.get_event_loop") as mock_loop_fn:
        mock_loop = MagicMock()
        mock_loop_fn.return_value = mock_loop

        mock_loop.run_in_executor = AsyncMock(
            return_value="something else"
        )

        # should not crash
        await cli_service.get_cli_command()