import os
import json
import asyncio
import redis.asyncio as aioredis
import uuid
from channels import IMAGE_ANNOTATED, IMAGE_EMBEDDED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


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


# TODO implement this function                
async def embed_image(data: dict):
    """funciton to embed the image in the message"""
    print(f"[embed_image] embedding image: {data.get('image_id')}")

    # mock embedded data
    embedded_data = {"embedded_data" : "sample embedded data"}
    new_data = data | embedded_data

    print(f"[embed_image] done embedding {data.get('image_id')}!")
    await send_image_embedded_message(new_data)


async def send_image_embedded_message(data : dict):
    """publish to IMAGE_ANNOTATED CHANNEL after successfully annotated"""
    payload = json.dumps(data)
    await r.publish(IMAGE_EMBEDDED, payload)
    print(f"[annotated_image] Sent message to {IMAGE_EMBEDDED}")