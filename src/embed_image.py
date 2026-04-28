import os
import json
import asyncio
import redis.asyncio as aioredis
from channels import IMAGE_ANNOTATED, IMAGE_EMBEDDED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

# Hardcoded bounding box vectors per image_id.
# Each vector is the 4 corners of a bounding box in [x1,y1, x2,y1, x2,y2, x1,y2] order.
IMAGE_VECTORS = {
    "dogs13": [
        [118,  30, 220,  30, 220, 210, 118, 210],
        [ 28, 220, 148, 220, 148, 380,  28, 380],
        [ 55, 340, 240, 340, 240, 490,  55, 490],
        [148, 185, 310, 185, 310, 460, 148, 460],
        [265, 130, 455, 130, 455, 430, 265, 430],
        [370,  28, 555,  28, 555, 240, 370, 240],
        [430, 195, 590, 195, 590, 450, 430, 450],
        [300, 330, 520, 330, 520, 505, 300, 505],
        [555, 195, 710, 195, 710, 430, 555, 430],
        [700, 215, 845, 215, 845, 455, 700, 455],
        [790,  28, 940,  28, 940, 230, 790, 230],
        [855, 270, 1010, 270, 1010, 480, 855, 480],
    ],
    "dogs1": [
        [305, 68, 750, 68, 750, 560, 305, 560],
    ],
    "cats2": [
        [  2,  2, 160,  2, 160, 180,   2, 180],
        [145,  8, 275,  8, 275, 178, 145, 178],
    ],
    "cats3": [
        [ 75, 155, 450, 155, 450, 885,  75, 885],   # Orange kitten (left)
        [490,  65, 870,  65, 870, 885, 490, 885],   # Black kitten (center)
        [940, 255, 1340, 255, 1340, 885, 940, 885], # Orange kitten (right)
    ],
}


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(IMAGE_ANNOTATED)
    print(f"[embed_image] Subscribed to '{IMAGE_ANNOTATED}', waiting for messages...")
 
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = json.loads(message["data"])
            if data.get("image_path"):
                # Each message is handled as its own concurrent task —
                # a slow upload won't block the next incoming message
                task = asyncio.create_task(embed_image(data))
                task.add_done_callback(
                    lambda t: t.exception() and print(f"[embed_image] task failed: {t.exception()}")
                )
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()


async def embed_image(data: dict):
    """Embed the image using hardcoded bounding box vectors keyed by image_id."""
    image_id = data.get("image_id")
    print(f"[embed_image] Embedding image: {image_id}")

    vectors = IMAGE_VECTORS.get(image_id, [])

    if not vectors:
        print(f"[embed_image] Warning: no vectors found for image_id '{image_id}'")

    embedded_data = {
        "image_id":   image_id,
        "image_path": data.get("image_path"),
        "vectors":    vectors,
        "confidence": 0.95,
        "timestamp":  data.get("timestamp"),
    }

    print(f"[embed_image] Done embedding '{image_id}' ({len(vectors)} vector(s))")
    await send_image_embedded_message(embedded_data)


async def send_image_embedded_message(data : dict):
    """publish to IMAGE_EMBEDDED CHANNEL after successfully embedded"""
    payload = json.dumps(data)
    await r.publish(IMAGE_EMBEDDED, payload)
    print(f"[embedded_image] Sent message to {IMAGE_EMBEDDED}")