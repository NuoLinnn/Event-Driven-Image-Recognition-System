import os
import json
import asyncio
import redis.asyncio as aioredis
import uuid
from channels import IMAGE_UPLOADED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(IMAGE_UPLOADED)
    print(f"[embed_image] Subscribed to '{IMAGE_UPLOADED}', waiting for messages...")
 
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
    print(f"[embed_image] embedding image: {data.get("image_id")}")
    return