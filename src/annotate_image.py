import os
import json
import asyncio
import redis.asyncio as aioredis
import uuid
from channels import IMAGE_PROCESSING_REQUESTED, IMAGE_ANNOTATED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(IMAGE_PROCESSING_REQUESTED)
    print(f"[annotate_image] Subscribed to '{IMAGE_PROCESSING_REQUESTED}', waiting for messages...")
 
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        if data.get("image_path"):
            # Each message is handled as its own concurrent task —
            # a slow upload won't block the next incoming message
            asyncio.create_task(annotate_image(data))


# TODO implement this function                
async def annotate_image(data: dict):
    """funciton to annotate the image in the message"""
    print(f"[annotate_image] annotating image: {data.get("image_id")}...")
    
    # mock annotated data
    annotated_data = {"annotated_data" : "sample data"}
    new_data = data | annotated_data

    print(f"[annotate_image] done annotating {data.get("image_id")}!")
    await send_image_annotated_message(new_data)


async def send_image_annotated_message(data : dict):
    """publish to IMAGE_ANNOTATED CHANNEL after successfully annotated"""
    payload = json.dumps(data)
    await r.publish(IMAGE_ANNOTATED, payload)
    print(f"[annotated_image] Sent message to {IMAGE_ANNOTATED}")