import os
import json
import redis
from channels import IMAGE_UPLOAD_REQUESTED

# Check extension type
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


# Connect to REDIS
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


# Create a function to take an image file from the cli_service
def upload_from_input(image_path: str):
    ext = os.path.splitext(image_path)[-1].lower()
 
    if ext not in ALLOWED_EXTENSIONS:
        print(f"Rejected: '{image_path}' is not a supported image type ({ext})")
        return
 
    if not os.path.exists(image_path):
        print(f"Rejected: file not found at '{image_path}'")
        return
 
    print(f"Uploading image: {image_path}")
    # TODO: add upload logic
    # Add event data to REDIS
    stream_name = "image_uploads"
    data = {
        "filename" image_path,
        "status": "pending",
        "timestamp": time.time()
    }

    message_id = r.xadd(stream_name, data)
 
 
def listen():
    pubsub = r.pubsub()
    pubsub.subscribe(IMAGE_UPLOAD_REQUESTED)
    print(f"Subscribed to '{IMAGE_UPLOAD_REQUESTED}', waiting for messages...")
 
    for message in pubsub.listen():
        if message["type"] != "message":
            continue
 
        data = json.loads(message["data"])
        image_path = data.get("image_path")
 
        if image_path:
            upload_from_input(image_path)
 
 
if __name__ == "__main__":
    listen()