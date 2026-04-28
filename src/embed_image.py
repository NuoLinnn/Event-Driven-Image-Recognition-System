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
    # dogs13 uses a random coordinate in Boston for lat_long
    "dogs13": [
        {"object1" : {"box1": [118,  30, 220,  30, 220, 210, 118, 210], "lat_long" : [42.3741, -71.0372]}},
        {"object2" : {"box2": [28, 220, 148, 220, 148, 380,  28, 380],  "lat_long" : [42.3741, -71.0372]}},
        {"object3" : {"box3": [55, 340, 240, 340, 240, 490,  55, 490],  "lat_long" : [42.3741, -71.0372]}},
        {"object4" : {"box4": [148, 185, 310, 185, 310, 460, 148, 460],  "lat_long" : [42.3741, -71.0372]}},
        {"object5" : {"box5": [265, 130, 455, 130, 455, 430, 265, 430],  "lat_long" : [42.3741, -71.0372]}},
        {"object6" : {"box6": [370,  28, 555,  28, 555, 240, 370, 240],  "lat_long" : [42.3741, -71.0372]}},
        {"object7" : {"box7": [430, 195, 590, 195, 590, 450, 430, 450],  "lat_long" : [42.3741, -71.0372]}},
        {"object8" : {"box8": [300, 330, 520, 330, 520, 505, 300, 505],  "lat_long" : [42.3741, -71.0372]}},
        {"object9" : {"box9": [555, 195, 710, 195, 710, 430, 555, 430],  "lat_long" : [42.3741, -71.0372]}},
        {"object10" : {"box10": [700, 215, 845, 215, 845, 455, 700, 455],  "lat_long" : [42.3741, -71.0372]}},
        {"object11" : {"box11": [790,  28, 940,  28, 940, 230, 790, 230],  "lat_long" : [42.3741, -71.0372]}},
        {"object12" : {"box12": [855, 270, 1010, 270, 1010, 480, 855, 480],  "lat_long" : [42.3741, -71.0372]}},
    ],

    # dogs1 has the same area (Boston) but a slighty different lat_long
    "dogs1": [
        {"object1" : {"box1": [305, 68, 750, 68, 750, 560, 305, 560], "lat_long" : [42.3598, -71.0921]}},
    ],

    # cats2 uses a random coordinate in New York for lat_long
    "cats2": [
        {"object1" : {"box1": [  2,  2, 160,  2, 160, 180,   2, 180], "lat_long" : [40.7282, -73.9942]}},
        {"object2" : {"box2": [145,  8, 275,  8, 275, 178, 145, 178], "lat_long" : [40.7282, -73.9942]}},
    ],

    # cats3 uses another random coordinate in New York for lat_long
    "cats3": [
        {"object1" : {"box1": [75, 155, 450, 155, 450, 885,  75, 885], "lat_long" : [40.6892, -73.9442]}},   # Orange kitten (left)
        {"object2" : {"box2": [490,  65, 870,  65, 870, 885, 490, 885], "lat_long" : [40.6892, -73.9442]}},   # Black kitten (center)
        {"object3" : {"box3": [940, 255, 1340, 255, 1340, 885, 940, 885], "lat_long" : [40.6892, -73.9442]}}, # Orange kitten (right)
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

    # Hardcode embedded_data based on image id
    vectors = IMAGE_VECTORS.get(image_id)
    if vectors is None:
        print(f"[embed_image] No vectors found for image_id '{image_id}', skipping.")
        return


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