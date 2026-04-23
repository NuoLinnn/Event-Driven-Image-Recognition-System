import os
import json
import asyncio
import redis.asyncio as aioredis
from channels import IMAGE_UPLOADED, IMAGE_ANNOTATED, IMAGE_EMBEDDED, IMAGE_PROCESSING_REQUESTED, IMAGE_READY

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

# Redis key patterns for tracking per-image completion state
PROCESSING_STATE_PREFIX = "processing_state:"
IMAGE_READY_TTL = 60 * 60  # 1 hour — clean up state keys automatically


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(*CHANNEL_HANDLERS)
    print(f"[process_image] Subscribed to '{list(CHANNEL_HANDLERS.keys())}', waiting for messages...")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = json.loads(message["data"])
            channel = message["channel"]
            handler = CHANNEL_HANDLERS.get(channel)

            if handler:
                task = asyncio.create_task(handler(data))
                task.add_done_callback(
                    lambda t: t.exception() and print(f"[process_image] task failed: {t.exception()}")
                )
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()


async def send_image_processing_requested_message(data: dict):
    """Fan out to annotation and embedding services."""
    payload = json.dumps(data)
    await r.publish(IMAGE_PROCESSING_REQUESTED, payload)
    print(f"[process_image] Sent message to {IMAGE_PROCESSING_REQUESTED}")


async def send_image_ready_message(image_id: str):
    """Publish IMAGE_READY once both annotation and embedding are confirmed."""
    state_key = f"{PROCESSING_STATE_PREFIX}{image_id}"
    state_raw = await r.get(state_key)

    if not state_raw:
        print(f"[process_image] Warning: no state found for '{image_id}' when sending IMAGE_READY")
        return

    payload = json.dumps(json.loads(state_raw) | {"status": "ready"})
    await r.publish(IMAGE_READY, payload)
    print(f"[process_image] Published IMAGE_READY for '{image_id}'")


async def process_image(data: dict):
    """Triggered on IMAGE_UPLOADED — initialise state and fan out to processing services."""
    image_id = data.get("image_id")
    print(f"[process_image] Processing image: {image_id}")

    state_key = f"{PROCESSING_STATE_PREFIX}{image_id}"
    try:
        await r.set(state_key, json.dumps({"image_id": image_id, "image_path": data.get("image_path")}), ex=IMAGE_READY_TTL)
    except Exception as e:
        print(f"[process_image] Warning: could not persist state for '{image_id}': {e}")

    await send_image_processing_requested_message(data)

async def _mark_complete(image_id: str, field: str, data: dict):
    """Merge incoming data into per-image state, then check the barrier."""
    state_key = f"{PROCESSING_STATE_PREFIX}{image_id}"
    lock_key = f"{state_key}:lock"

    try:
        async with r.lock(lock_key, timeout=5):
            state_raw = await r.get(state_key)
            state = json.loads(state_raw) if state_raw else {}

            state[field] = data
            await r.set(state_key, json.dumps(state), ex=IMAGE_READY_TTL)

            annotated_done = "annotated" in state
            embedded_done = "embedded" in state
    except Exception as e:
        print(f"[process_image] Warning: could not update state for '{image_id}': {e}")
        return

    if annotated_done and embedded_done:
        print(f"[process_image] Both steps complete for '{image_id}' — triggering IMAGE_READY")
        await send_image_ready_message(image_id)

async def process_embedded(data: dict):
    """Triggered on IMAGE_EMBEDDED — record completion and check barrier."""
    image_id = data.get("image_id")
    print(f"[process_image] Handling embedded: {image_id}")
    await _mark_complete(image_id, "embedded", {
        "embedding_key": data.get("embedding_key"),
        "embedding_dim": data.get("embedding_dim"),
    })


async def process_annotated(data: dict):
    """Triggered on IMAGE_ANNOTATED — record completion and check barrier."""
    image_id = data.get("image_id")
    print(f"[process_image] Handling annotated: {image_id}")
    await _mark_complete(image_id, "annotated", {
        "annotations": data.get("annotations"),
    })


# Channels this module listens to
CHANNEL_HANDLERS = {
    IMAGE_UPLOADED: process_image,
    IMAGE_ANNOTATED: process_annotated,
    IMAGE_EMBEDDED: process_embedded,
}