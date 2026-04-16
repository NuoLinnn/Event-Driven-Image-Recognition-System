import os
import json
import asyncio
import redis.asyncio as aioredis
import uuid
from channels import IMAGE_UPLOAD_REQUESTED, IMAGE_UPLOADED

# Check extension type
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


async def upload_from_input(data: dict):
    image_id = data.get("image_id")
    image_path = data.get("image_path")
    timestamp = data.get("timestamp")
 
    ext = os.path.splitext(image_path)[-1].lower()
 
    if ext not in ALLOWED_EXTENSIONS:
        print(f"[upload_image] Rejected: '{image_path}' is not a supported image type ({ext})")
        return
 
    if not os.path.exists(image_path):
        print(f"[upload_image] Rejected: file not found at '{image_path}'")
        return
 
    print(f"[upload_image] Uploading image: {image_path}")
    # TODO: add upload logic here (e.g. copy to storage, call upload API)
    
    print(f"[upload_image] done uploading image {image_id}!")
    await send_image_uploaded_message(image_id,image_path, timestamp)
 

async def send_image_uploaded_message(image_id: str, image_path: str, timestamp: float):
    """Publish to IMAGE_UPLOADED channel after a successful upload."""
    payload = json.dumps({
        "image_id": image_id,
        "image_path": image_path,
        "timestamp": timestamp,
        "status": "uploaded"
    })
    await r.publish(IMAGE_UPLOADED, payload)
    print(f"[upload_image] Sent message to {IMAGE_UPLOADED}")


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(IMAGE_UPLOAD_REQUESTED)
    print(f"[upload_image] Subscribed to '{IMAGE_UPLOAD_REQUESTED}', waiting for messages...")
 
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
 
        data = json.loads(message["data"])
        if data.get("image_path"):
            # Each message is handled as its own concurrent task —
            # a slow upload won't block the next incoming message
            asyncio.create_task(upload_from_input(data))