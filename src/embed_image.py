import os
import json
import asyncio
import redis.asyncio as aioredis
import uuid
from channels import IMAGE_PROCESSING_REQUESTED, IMAGE_EMBEDDED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(IMAGE_PROCESSING_REQUESTED)
    print(f"[embed_image] Subscribed to '{IMAGE_PROCESSING_REQUESTED}', waiting for messages...")
 
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        if data.get("image_path"):
            # Each message is handled as its own concurrent task —
            # a slow upload won't block the next incoming message
            asyncio.create_task(embed_image(data))


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