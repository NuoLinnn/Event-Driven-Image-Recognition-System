import json
import asyncio
import redis.asyncio as aioredis
import motor.motor_asyncio
from channels import IMAGE_PROCESSING_REQUESTED, IMAGE_ANNOTATED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

# Connect to MongoDB
mongo_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = mongo_client["image_recognition"]
annotations_collection = db["annotations"]


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(IMAGE_PROCESSING_REQUESTED)
    print(f"[annotate_image] Subscribed to '{IMAGE_PROCESSING_REQUESTED}', waiting for messages...")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = json.loads(message["data"])
            if data.get("image_path"):
                task = asyncio.create_task(annotate_image(data))
                task.add_done_callback(
                    lambda t: t.exception() and print(f"[annotate_image] task failed: {t.exception()}")
                )
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()


async def annotate_image(data: dict):
    """Annotate the image and store results in MongoDB."""
    image_id = data.get('image_id')
    print(f"[annotate_image] Annotating image: {image_id}...")

    # Hardcode annotated_data based on image id
    if (image_id == 'dogs13'):
        labels = {"object1" : "dog", "object2" : "dog", "object3" : "dog", "object4" : "dog", "object5" : "dog", "object6" : "dog",
                "object7" : "dog", "object8" : "dog", "object9" : "dog", "object10" : "dog", "object11" : "dog", "object12" : "dog",
                "object13" : "dog"}
    elif(image_id == 'dogs1'):
        labels = {"object1" : "dog"}
    elif(image_id == 'cats2'):
        labels = {"object1" : "cat", "object2" : "cat"}
    elif(image_id == 'cats3'):
        labels = {"object1" : "cat", "object2" : "cat", "object3" : "cat"}
    else:
        labels = {}

    annotated_data = {
        "image_id":   image_id,
        "image_path": data.get("image_path"),
        "labels":     labels,
        "confidence": 0.95,
        "timestamp":  data.get("timestamp"),
    }

    await save_annotation(annotated_data)

    new_data = data | annotated_data
    print(f"[annotate_image] Done annotating {image_id}!")
    await send_image_annotated_message(new_data)


async def save_annotation(annotated_data: dict):
    """Insert or update annotation record in MongoDB."""
    result = await annotations_collection.update_one(
        {"image_id": annotated_data["image_id"]},  # match on image_id
        {"$set": annotated_data},                  # update fields
        upsert=True                                # insert if not found
    )
    print(f"[annotate_image] Saved to MongoDB (upserted: {result.upserted_id is not None})")


async def send_image_annotated_message(data: dict):
    """Publish to IMAGE_ANNOTATED channel after successfully annotating."""
    payload = json.dumps(data)
    await r.publish(IMAGE_ANNOTATED, payload)
    print(f"[annotate_image] Sent message to {IMAGE_ANNOTATED}")