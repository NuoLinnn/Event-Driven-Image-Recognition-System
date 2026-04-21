import os
import json
import asyncio
import aiosqlite
import redis.asyncio as aioredis
from channels import IMAGE_UPLOAD_REQUESTED, IMAGE_UPLOADED

# ── Config ────────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images.db")

# ── Redis ─────────────────────────────────────────────────────────────────────

r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

# ── Database ──────────────────────────────────────────────────────────────────

async def init_db():
    """Create the images table if it doesn't already exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS images (
                image_id  TEXT PRIMARY KEY,
                image_path TEXT NOT NULL,
                timestamp  REAL NOT NULL,
                status     TEXT NOT NULL,
                image_blob BLOB NOT NULL
            )
        """)
        await db.commit()
    print(f"[upload_image] Database ready at {DB_PATH}")


async def save_image_to_db(image_id: str, image_path: str, timestamp: float, image_bytes: bytes):
    """Insert image metadata and raw bytes into SQLite."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO images (image_id, image_path, timestamp, status, image_blob)
            VALUES (?, ?, ?, ?, ?)
        """, (image_id, image_path, timestamp, "uploaded", image_bytes))
        await db.commit()
    print(f"[upload_image] Saved '{image_id}' to database ({len(image_bytes):,} bytes)")

# ── Upload logic ──────────────────────────────────────────────────────────────

async def upload_from_input(data: dict):
    image_id   = data.get("image_id")
    image_path = data.get("image_path")
    timestamp  = data.get("timestamp")

    ext = os.path.splitext(image_path)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        print(f"[upload_image] Rejected: '{image_path}' is not a supported image type ({ext})")
        return

    if not os.path.exists(image_path):
        print(f"[upload_image] Rejected: file not found at '{image_path}'")
        return

    # Build destination path and check for duplicates
    dest_filename = f"{image_id}{ext}"
    dest_path = os.path.join(UPLOAD_DEST_DIR, dest_filename)

    if os.path.exists(dest_path):
        print(f"[upload_image] Warning: image_id '{image_id}' already exists at '{dest_path}', skipping.")
        return

    print(f"[upload_image] Reading image: {image_path}")
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
    except OSError as e:
        print(f"[upload_image] ERROR reading file: {e}")
        return

    try:
        await save_image_to_db(image_id, image_path, timestamp, image_bytes)
    except Exception as e:
        print(f"[upload_image] ERROR saving to database: {e}")
        return

    print(f"[upload_image] Done uploading image '{image_id}'!")
    await send_image_uploaded_message(image_id, image_path, timestamp)


async def send_image_uploaded_message(image_id: str, image_path: str, timestamp: float):
    """Publish to IMAGE_UPLOADED channel after a successful upload."""
    payload = json.dumps({
        "image_id":   image_id,
        "image_path": image_path,
        "timestamp":  timestamp,
        "status":     "uploaded",
    })
    await r.publish(IMAGE_UPLOADED, payload)
    print(f"[upload_image] Sent message to {IMAGE_UPLOADED}")

# ── Listener ──────────────────────────────────────────────────────────────────

async def listen():
    await init_db()

    pubsub = r.pubsub()
    await pubsub.subscribe(IMAGE_UPLOAD_REQUESTED)
    print(f"[upload_image] Subscribed to '{IMAGE_UPLOAD_REQUESTED}', waiting for messages...")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = json.loads(message["data"])
            if data.get("image_path"):
                task = asyncio.create_task(upload_from_input(data))
                task.add_done_callback(
                    lambda t: t.exception() and print(f"[upload_image] task failed: {t.exception()}")
                )
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()