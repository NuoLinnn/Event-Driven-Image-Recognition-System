"""
Integration tests for each independent pipeline entry point.

Each test publishes directly to a Redis channel and listens for the
expected downstream output — no CLI or full stack required.

Requirements:
    pip install pytest pytest-asyncio redis

Usage:
    pytest test_pipelines.py -v
    pytest test_pipelines.py -v -k "test_upload"   # run one test
"""

import pytest_asyncio
import asyncio
import json
import time
import pytest
import redis.asyncio as aioredis

from channels import (
    IMAGE_UPLOAD_REQUESTED,
    IMAGE_UPLOADED,
    IMAGE_PROCESSING_REQUESTED,
    IMAGE_PROCESSED,
    IMAGE_ANNOTATED,
    IMAGE_EMBEDDED,
    QUERY_REQUESTED,
    QUERY_ANSWERED,
)

# ── Config ────────────────────────────────────────────────────────────────────

REDIS_HOST = "localhost"
REDIS_PORT = 6379
TIMEOUT    = 10   # seconds to wait for a downstream message before failing

# A real file path is needed for upload/process tests because upload_image
# validates os.path.exists(). Point this at any small image on your machine.
SAMPLE_IMAGE_PATH = "../test_images/dogs.jpg"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def wait_for_message(r: aioredis.Redis, channel: str, timeout: int = TIMEOUT) -> dict:
    """Subscribe to `channel` and return the first data payload received."""
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    try:
        deadline = time.monotonic() + timeout
        async for message in pubsub.listen():
            if time.monotonic() > deadline:
                raise TimeoutError(f"No message on '{channel}' within {timeout}s")
            if message["type"] != "message":
                continue
            return json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


async def publish(r: aioredis.Redis, channel: str, payload: dict):
    await r.publish(channel, json.dumps(payload))


def make_image_payload(image_id: str = "test_img", path: str = SAMPLE_IMAGE_PATH) -> dict:
    return {
        "image_id": image_id,
        "image_path": path,
        "timestamp": time.time(),
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def r():
    """Shared async Redis client for each test."""
    client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    yield client
    await client.aclose()


# ── Entry point 1: image.upload.requested → image.uploaded ───────────────────

class TestUploadPipeline:
    """
    Start: publish to image.upload.requested
    Expects: upload_image module to emit image.uploaded
    """

    @pytest.mark.asyncio
    async def test_upload_emits_image_uploaded(self, r):
        payload = make_image_payload("upload_test")

        listener = asyncio.create_task(wait_for_message(r, IMAGE_UPLOADED))
        await asyncio.sleep(0.1)  # give the subscriber a moment to register
        await publish(r, IMAGE_UPLOAD_REQUESTED, payload)

        result = await asyncio.wait_for(listener, timeout=TIMEOUT)

        assert result["image_id"] == "upload_test"
        assert result["status"] == "uploaded"
        assert result["image_path"] == payload["image_path"]

    @pytest.mark.asyncio
    async def test_upload_rejected_bad_extension(self, r):
        """upload_image should silently reject unsupported file types.
        We verify no image.uploaded message arrives within the timeout."""
        payload = make_image_payload("bad_ext_test", path="/tmp/document.pdf")

        listener = asyncio.create_task(wait_for_message(r, IMAGE_UPLOADED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_UPLOAD_REQUESTED, payload)

        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            await asyncio.wait_for(listener, timeout=3)

    @pytest.mark.asyncio
    async def test_upload_rejected_missing_file(self, r):
        """upload_image should silently reject paths that don't exist."""
        payload = make_image_payload("missing_file_test", path="/tmp/does_not_exist.jpg")

        listener = asyncio.create_task(wait_for_message(r, IMAGE_UPLOADED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_UPLOAD_REQUESTED, payload)

        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            await asyncio.wait_for(listener, timeout=3)


# ── Entry point 2: image.uploaded → image.processing.requested ───────────────

class TestProcessPipeline:
    """
    Start: publish to image.uploaded  (skips upload_image entirely)
    Expects: process_image module to emit image.processing.requested
    """

    @pytest.mark.asyncio
    async def test_process_emits_processing_requested(self, r):
        payload = make_image_payload("process_test")
        payload["status"] = "uploaded"

        listener = asyncio.create_task(wait_for_message(r, IMAGE_PROCESSING_REQUESTED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_UPLOADED, payload)

        result = await asyncio.wait_for(listener, timeout=TIMEOUT)

        assert result["image_id"] == "process_test"
        assert result["image_path"] == payload["image_path"]


# ── Entry point 3: image.processing.requested → image.annotated ──────────────

class TestAnnotatePipeline:
    """
    Start: publish to image.processing.requested  (skips upload + process)
    Expects: annotate_image module to emit image.annotated
    """

    @pytest.mark.asyncio
    async def test_annotate_emits_image_annotated(self, r):
        payload = make_image_payload("annotate_test")

        listener = asyncio.create_task(wait_for_message(r, IMAGE_ANNOTATED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_PROCESSING_REQUESTED, payload)

        result = await asyncio.wait_for(listener, timeout=TIMEOUT)

        assert result["image_id"] == "annotate_test"
        assert "annotated_data" in result, "annotated_data key missing from output"

    @pytest.mark.asyncio
    async def test_annotate_preserves_upstream_fields(self, r):
        """All fields from the triggering message should pass through."""
        payload = make_image_payload("annotate_passthrough_test")
        payload["extra_field"] = "should_survive"

        listener = asyncio.create_task(wait_for_message(r, IMAGE_ANNOTATED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_PROCESSING_REQUESTED, payload)

        result = await asyncio.wait_for(listener, timeout=TIMEOUT)

        assert result.get("extra_field") == "should_survive"


# ── Entry point 4: image.processing.requested → image.embedded ───────────────

class TestEmbedPipeline:
    """
    Start: publish to image.processing.requested  (skips upload + process)
    Expects: embed_image module to emit image.embedded
    """

    @pytest.mark.asyncio
    async def test_embed_emits_image_embedded(self, r):
        payload = make_image_payload("embed_test")

        listener = asyncio.create_task(wait_for_message(r, IMAGE_EMBEDDED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_PROCESSING_REQUESTED, payload)

        result = await asyncio.wait_for(listener, timeout=TIMEOUT)

        assert result["image_id"] == "embed_test"
        assert "embedded_data" in result, "embedded_data key missing from output"

    @pytest.mark.asyncio
    async def test_embed_preserves_upstream_fields(self, r):
        payload = make_image_payload("embed_passthrough_test")
        payload["extra_field"] = "should_survive"

        listener = asyncio.create_task(wait_for_message(r, IMAGE_EMBEDDED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_PROCESSING_REQUESTED, payload)

        result = await asyncio.wait_for(listener, timeout=TIMEOUT)

        assert result.get("extra_field") == "should_survive"


# ── Entry point 5: image.processing.requested → both annotate + embed ────────

class TestAnnotateAndEmbedConcurrent:
    """
    Verifies that annotate_image and embed_image both fire from a single
    image.processing.requested message (they share the same subscription).
    """

    @pytest.mark.asyncio
    async def test_both_emit_from_single_processing_message(self, r):
        payload = make_image_payload("concurrent_test")

        annotated_task = asyncio.create_task(wait_for_message(r, IMAGE_ANNOTATED))
        embedded_task  = asyncio.create_task(wait_for_message(r, IMAGE_EMBEDDED))
        await asyncio.sleep(0.1)
        await publish(r, IMAGE_PROCESSING_REQUESTED, payload)

        annotated, embedded = await asyncio.gather(
            asyncio.wait_for(annotated_task, timeout=TIMEOUT),
            asyncio.wait_for(embedded_task,  timeout=TIMEOUT),
        )

        assert annotated["image_id"] == "concurrent_test"
        assert embedded["image_id"]  == "concurrent_test"


# ── Entry point 6: query.requested → query.answered ──────────────────────────

class TestQueryPipeline:
    """
    Start: publish to query.requested  (completely independent of image pipeline)
    Expects: query_service to emit query.answered
    """

    @pytest.mark.asyncio
    async def test_query_emits_answered(self, r):
        payload = {"query": "show me images of cats"}

        listener = asyncio.create_task(wait_for_message(r, QUERY_ANSWERED))
        await asyncio.sleep(0.1)
        await publish(r, QUERY_REQUESTED, payload)

        result = await asyncio.wait_for(listener, timeout=TIMEOUT)

        assert "answer" in result, "answer key missing from query.answered payload"

    @pytest.mark.asyncio
    async def test_query_missing_query_field_is_ignored(self, r):
        """query_service guards on data.get('query') — empty payload should be dropped."""
        payload = {"not_a_query": "something else"}

        listener = asyncio.create_task(wait_for_message(r, QUERY_ANSWERED))
        await asyncio.sleep(0.1)
        await publish(r, QUERY_REQUESTED, payload)

        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            await asyncio.wait_for(listener, timeout=3)