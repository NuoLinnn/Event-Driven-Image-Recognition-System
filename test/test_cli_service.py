import os
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import time

# ---------------------------------------------------------------------------
# Helpers / stubs so the module can be imported without real Redis / tkinter
# ---------------------------------------------------------------------------

# Stub out the `channels` module before importing cli_service
import sys
import types

channels_stub = types.ModuleType("channels")
channels_stub.IMAGE_UPLOAD_REQUESTED = "image.upload.requested"
channels_stub.IMAGE_UPLOADED = "image.uploaded"
channels_stub.IMAGE_PROCESSED = "image.processed"
channels_stub.IMAGE_ANNOTATED = "image.annotated"
channels_stub.IMAGE_EMBEDDED = "image.embedded"
sys.modules.setdefault("channels", channels_stub)

# Stub redis so no real connection is attempted at import time
redis_stub = types.ModuleType("redis")
redis_asyncio_stub = types.ModuleType("redis.asyncio")
redis_asyncio_stub.Redis = MagicMock(return_value=MagicMock())
redis_stub.Redis = MagicMock(return_value=MagicMock())
redis_stub.asyncio = redis_asyncio_stub
sys.modules.setdefault("redis", redis_stub)
sys.modules.setdefault("redis.asyncio", redis_asyncio_stub)

# Now import the module under test (adjust name / path as needed)
import importlib, importlib.util, pathlib

SOURCE = pathlib.Path(__file__).parent.parent / "src" / "cli_service.py"

# If running without the actual source file alongside, fall back to loading
# from its real location wherever you keep it.
spec = importlib.util.spec_from_file_location("cli_service", SOURCE)
cli_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_service)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_redis_client():
    """Replace the module-level `r` with an AsyncMock for every test."""
    mock_r = AsyncMock()
    mock_r.publish = AsyncMock(return_value=1)
    with patch.object(cli_service, "r", mock_r):
        yield mock_r


# ===========================================================================
# pick_image_file
# ===========================================================================

class TestPickImageFile:
    def test_returns_path_when_user_selects_file(self):
        with patch("tkinter.Tk") as mock_tk, \
             patch("tkinter.filedialog.askopenfilename", return_value="/tmp/photo.jpg"):
            mock_root = MagicMock()
            mock_tk.return_value = mock_root

            result = cli_service.pick_image_file()

        assert result == "/tmp/photo.jpg"

    def test_returns_none_when_user_cancels(self):
        with patch("tkinter.Tk"), \
             patch("tkinter.filedialog.askopenfilename", return_value=""):
            result = cli_service.pick_image_file()

        assert result is None

    def test_tk_window_is_withdrawn_and_destroyed(self):
        with patch("tkinter.Tk") as mock_tk, \
             patch("tkinter.filedialog.askopenfilename", return_value=""):
            mock_root = MagicMock()
            mock_tk.return_value = mock_root
            cli_service.pick_image_file()

        mock_root.withdraw.assert_called_once()
        mock_root.destroy.assert_called_once()

    def test_dialog_is_brought_to_front(self):
        with patch("tkinter.Tk") as mock_tk, \
             patch("tkinter.filedialog.askopenfilename", return_value=""):
            mock_root = MagicMock()
            mock_tk.return_value = mock_root
            cli_service.pick_image_file()

        mock_root.attributes.assert_called_once_with("-topmost", True)


# ===========================================================================
# pick_image_file_async
# ===========================================================================

class TestPickImageFileAsync:
    @pytest.mark.asyncio
    async def test_delegates_to_sync_version(self):
        with patch.object(cli_service, "pick_image_file", return_value="/tmp/img.png") as mock_sync:
            result = await cli_service.pick_image_file_async()

        assert result == "/tmp/img.png"
        mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_sync_returns_none(self):
        with patch.object(cli_service, "pick_image_file", return_value=None):
            result = await cli_service.pick_image_file_async()

        assert result is None


# ===========================================================================
# send_image_upload_requested_message
# ===========================================================================

class TestSendImageUploadRequestedMessage:
    @pytest.mark.asyncio
    async def test_publishes_to_correct_channel(self, mock_redis_client):
        await cli_service.send_image_upload_requested_message("/some/dir/photo.jpg")

        mock_redis_client.publish.assert_awaited_once()
        channel_arg = mock_redis_client.publish.call_args[0][0]
        assert channel_arg == channels_stub.IMAGE_UPLOAD_REQUESTED

    @pytest.mark.asyncio
    async def test_payload_contains_expected_keys(self, mock_redis_client):
        await cli_service.send_image_upload_requested_message("/some/dir/photo.jpg")

        raw_payload = mock_redis_client.publish.call_args[0][1]
        payload = json.loads(raw_payload)

        assert "image_id" in payload
        assert "image_path" in payload
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_image_id_is_filename_without_extension(self, mock_redis_client):
        await cli_service.send_image_upload_requested_message("/some/dir/my_photo.jpg")

        raw_payload = mock_redis_client.publish.call_args[0][1]
        payload = json.loads(raw_payload)

        assert payload["image_id"] == "my_photo"

    @pytest.mark.asyncio
    async def test_image_path_is_absolute(self, mock_redis_client):
        await cli_service.send_image_upload_requested_message("relative/path/photo.png")

        raw_payload = mock_redis_client.publish.call_args[0][1]
        payload = json.loads(raw_payload)

        assert os.path.isabs(payload["image_path"])

    @pytest.mark.asyncio
    async def test_timestamp_is_recent(self, mock_redis_client):
        before = time.time()
        await cli_service.send_image_upload_requested_message("/tmp/img.gif")
        after = time.time()

        raw_payload = mock_redis_client.publish.call_args[0][1]
        payload = json.loads(raw_payload)

        assert before <= payload["timestamp"] <= after

    @pytest.mark.asyncio
    async def test_payload_is_valid_json(self, mock_redis_client):
        await cli_service.send_image_upload_requested_message("/tmp/img.png")

        raw_payload = mock_redis_client.publish.call_args[0][1]
        # Should not raise
        parsed = json.loads(raw_payload)
        assert isinstance(parsed, dict)


# ===========================================================================
# get_cli_command
# ===========================================================================

class TestGetCliCommand:
    @pytest.mark.asyncio
    async def test_upload_flow_calls_send_when_file_exists(self, mock_redis_client, tmp_path):
        fake_image = tmp_path / "test.jpg"
        fake_image.write_bytes(b"fake")

        with patch("asyncio.get_event_loop") as mock_loop_fn:
            mock_loop = MagicMock()
            mock_loop_fn.return_value = mock_loop

            # First executor call → user input; second → file picker
            mock_loop.run_in_executor = AsyncMock(
                side_effect=["upload an image", str(fake_image)]
            )

            with patch.object(cli_service, "send_image_upload_requested_message", new=AsyncMock()) as mock_send:
                await cli_service.get_cli_command()

            mock_send.assert_awaited_once_with(str(fake_image))

    @pytest.mark.asyncio
    async def test_upload_flow_prints_error_when_file_missing(self, capsys):
        with patch("asyncio.get_event_loop") as mock_loop_fn:
            mock_loop = MagicMock()
            mock_loop_fn.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(
                side_effect=["upload an image", "/nonexistent/path/img.jpg"]
            )

            with patch.object(cli_service, "send_image_upload_requested_message", new=AsyncMock()) as mock_send:
                await cli_service.get_cli_command()

            mock_send.assert_not_awaited()

        captured = capsys.readouterr()
        assert "ERROR" in captured.out or "not found" in captured.out

    @pytest.mark.asyncio
    async def test_upload_flow_prints_message_when_no_file_selected(self, capsys):
        with patch("asyncio.get_event_loop") as mock_loop_fn:
            mock_loop = MagicMock()
            mock_loop_fn.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(
                side_effect=["upload an image", None]
            )

            with patch.object(cli_service, "send_image_upload_requested_message", new=AsyncMock()) as mock_send:
                await cli_service.get_cli_command()

            mock_send.assert_not_awaited()

        captured = capsys.readouterr()
        assert "No file selected" in captured.out

    @pytest.mark.asyncio
    async def test_query_topic_branch_prints_message(self, capsys):
        with patch("asyncio.get_event_loop") as mock_loop_fn:
            mock_loop = MagicMock()
            mock_loop_fn.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(return_value="query a topic")

            await cli_service.get_cli_command()

        captured = capsys.readouterr()
        assert "querying topic" in captured.out

    @pytest.mark.asyncio
    async def test_unknown_command_does_nothing(self):
        with patch("asyncio.get_event_loop") as mock_loop_fn:
            mock_loop = MagicMock()
            mock_loop_fn.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(return_value="do something else")

            with patch.object(cli_service, "send_image_upload_requested_message", new=AsyncMock()) as mock_send:
                # Should complete without error
                await cli_service.get_cli_command()

            mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_input_is_case_insensitive(self, tmp_path):
        fake_image = tmp_path / "photo.png"
        fake_image.write_bytes(b"data")

        with patch("asyncio.get_event_loop") as mock_loop_fn:
            mock_loop = MagicMock()
            mock_loop_fn.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(
                side_effect=["UPLOAD AN IMAGE", str(fake_image)]
            )

            with patch.object(cli_service, "send_image_upload_requested_message", new=AsyncMock()) as mock_send:
                await cli_service.get_cli_command()

            mock_send.assert_awaited_once()