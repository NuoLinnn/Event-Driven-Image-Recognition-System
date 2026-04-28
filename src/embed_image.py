import os
import json
import asyncio
import numpy as np
import faiss
import redis.asyncio as aioredis
from channels import IMAGE_ANNOTATED, IMAGE_EMBEDDED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

# ── FAISS setup ───────────────────────────────────────────────────────────────
VECTOR_DIM    = 2               # [lat, long]
INDEX_PATH    = "faiss_index.bin"
METADATA_PATH = "faiss_metadata.json"

if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
    print(f"[embed_image] Loaded FAISS index ({index.ntotal} vectors)")
else:
    index = faiss.IndexFlatL2(VECTOR_DIM)
    print("[embed_image] Created new FAISS index")

if os.path.exists(METADATA_PATH):
    with open(METADATA_PATH) as f:
        metadata_store: dict[str, dict] = json.load(f)
    print(f"[embed_image] Loaded metadata ({len(metadata_store)} entries)")
else:
    metadata_store: dict[str, dict] = {}

# ── Hardcoded image data ──────────────────────────────────────────────────────
IMAGE_VECTORS = {
    "dogs13": [
        {"object1":  {"box": [118,  30, 220,  30, 220, 210, 118, 210], "lat_long": [42.3741, -71.0372]}},
        {"object2":  {"box": [ 28, 220, 148, 220, 148, 380,  28, 380], "lat_long": [42.3741, -71.0372]}},
        {"object3":  {"box": [ 55, 340, 240, 340, 240, 490,  55, 490], "lat_long": [42.3741, -71.0372]}},
        {"object4":  {"box": [148, 185, 310, 185, 310, 460, 148, 460], "lat_long": [42.3741, -71.0372]}},
        {"object5":  {"box": [265, 130, 455, 130, 455, 430, 265, 430], "lat_long": [42.3741, -71.0372]}},
        {"object6":  {"box": [370,  28, 555,  28, 555, 240, 370, 240], "lat_long": [42.3741, -71.0372]}},
        {"object7":  {"box": [430, 195, 590, 195, 590, 450, 430, 450], "lat_long": [42.3741, -71.0372]}},
        {"object8":  {"box": [300, 330, 520, 330, 520, 505, 300, 505], "lat_long": [42.3741, -71.0372]}},
        {"object9":  {"box": [555, 195, 710, 195, 710, 430, 555, 430], "lat_long": [42.3741, -71.0372]}},
        {"object10": {"box": [700, 215, 845, 215, 845, 455, 700, 455], "lat_long": [42.3741, -71.0372]}},
        {"object11": {"box": [790,  28, 940,  28, 940, 230, 790, 230], "lat_long": [42.3741, -71.0372]}},
        {"object12": {"box": [855, 270, 1010, 270, 1010, 480, 855, 480], "lat_long": [42.3741, -71.0372]}},
    ],
    "dogs1": [
        {"object1": {"box": [305, 68, 750, 68, 750, 560, 305, 560], "lat_long": [42.3598, -71.0921]}},
    ],
    "cats2": [
        {"object1": {"box": [  2,  2, 160,  2, 160, 180,   2, 180], "lat_long": [40.7282, -73.9942]}},
        {"object2": {"box": [145,  8, 275,  8, 275, 178, 145, 178], "lat_long": [40.7282, -73.9942]}},
    ],
    "cats3": [
        {"object1": {"box": [ 75, 155, 450, 155, 450, 885,  75, 885], "lat_long": [40.6892, -73.9442]}},
        {"object2": {"box": [490,  65, 870,  65, 870, 885, 490, 885], "lat_long": [40.6892, -73.9442]}},
        {"object3": {"box": [940, 255, 1340, 255, 1340, 885, 940, 885], "lat_long": [40.6892, -73.9442]}},
    ],
}

# ── Sync FAISS functions (wrapped in executor to avoid blocking event loop) ───
def _add_object_to_index(faiss_id: int, image_id: str, object_name: str,
                          box: list, lat_long: list):
    """Sync — adds one [lat, long] vector to FAISS and saves metadata."""
    vec = np.array([lat_long], dtype=np.float32)  # shape (1, 2)
    index.add(vec)

    metadata_store[str(faiss_id)] = {
        "image_id":    image_id,
        "object_name": object_name,
        "box":         box,
        "lat_long":    lat_long,
    }


def _save_index():
    """Sync — persists FAISS index and metadata to disk."""
    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata_store, f, indent=2)
    print(f"[embed_image] Saved index ({index.ntotal} vectors) and metadata to disk")


async def add_object_to_index(faiss_id: int, image_id: str, object_name: str,
                               box: list, lat_long: list):
    """Async wrapper — runs sync FAISS call in a thread executor."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _add_object_to_index, faiss_id, image_id, object_name, box, lat_long
    )


async def save_index():
    """Async wrapper — runs sync disk write in a thread executor."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _save_index)


# ── Redis listener ────────────────────────────────────────────────────────────
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
                task = asyncio.create_task(embed_image(data))
                task.add_done_callback(
                    lambda t: t.exception() and print(f"[embed_image] task failed: {t.exception()}")
                )
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()


async def embed_image(data: dict):
    """Embed each object's lat/long into FAISS at the object level."""
    image_id = data.get("image_id")
    print(f"[embed_image] Embedding image: {image_id}")

    objects = IMAGE_VECTORS.get(image_id)
    if not objects:
        print(f"[embed_image] No vectors found for '{image_id}', skipping.")
        return

    for obj_dict in objects:
        for object_name, obj_data in obj_dict.items():
            lat_long = obj_data["lat_long"]   # [lat, long] — this is what FAISS stores
            box      = obj_data["box"]
            faiss_id = index.ntotal           # next available ID before adding

            await add_object_to_index(
                faiss_id    = faiss_id,
                image_id    = image_id,
                object_name = object_name,
                box         = box,
                lat_long    = lat_long,
            )
            print(f"[embed_image] Added {image_id}/{object_name} → FAISS ID {faiss_id} | lat_long {lat_long}")

    await save_index()

    embedded_data = {
        "image_id":    image_id,
        "image_path":  data.get("image_path"),
        "num_objects": len(objects),
        "confidence":  data.get("confidence", 0.95),
        "timestamp":   data.get("timestamp"),
    }

    print(f"[embed_image] Done embedding '{image_id}' ({len(objects)} object(s))")
    await send_image_embedded_message(embedded_data)


async def send_image_embedded_message(data: dict):
    """Publish to IMAGE_EMBEDDED channel after successfully embedding."""
    payload = json.dumps(data)
    await r.publish(IMAGE_EMBEDDED, payload)
    print(f"[embed_image] Sent message to {IMAGE_EMBEDDED}")