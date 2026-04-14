import os
import redis
import time
import process_image

# Using REDIS:
r = redis.Redis(host='localhost', port=6379, db=0)

# Create a function to take an image file from the cli_service
def upload_from_input(user_id, image_path):
    
    # Add event data to REDIS
    stream_name = "image_uploads"
    data = {
        "user_id": user_id,
        "filename" image_path,
        "status": "pending",
        "timestamp": time.time()
    }

    message_id = r.xadd(stream_name, data)




