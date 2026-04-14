import os
import json
import redis
import tkinter as tk
from tkinter import filedialog
from channels import IMAGE_UPLOAD_REQUESTED
import time

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

ALLOWED_EXTENSIONS = [
    ("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tiff"),
    ("All files", "*.*")
]

def event(topic: str, payload: dict) -> dict:
    return {
        "topic": topic,
        "event_id": str(uuid.uuid4()),
        "payload": payload,
        "timestamp": time.time()
    }


def pick_image_file() -> str | None:
    """open file explorer for user to navigate to image"""
    root = tk.Tk()
    root.withdraw()  # hide the empty tkinter window
    root.attributes("-topmost", True)  # bring dialog to front
    path = filedialog.askopenfilename(
        title="Select an image",
        filetypes=ALLOWED_EXTENSIONS
    )
    root.destroy()
    return path or None

# Create a function to submit a request from the command line
def get_cli_command():
    ask = input("What do you want to do: 'upload an image', or 'query a topic'?")
    if ask.lower() == "upload an image":
        # Input code to point to functions to upload and process image
        # Send information to the upload_image service
        image_path = pick_image_file()

        # return if file not found
        if not os.path.exists(image_path):
            print(f"ERROR: file not found at {image_path}")
            return

        # send payload to IMAGE_UPLOAD_REQUESTED
        payload = json.dumps({"image_path" : os.path.abspath(image_path)})
        r.publish(IMAGE_UPLOAD_REQUESTED, payload)
        print(f"send image to {IMAGE_UPLOAD_REQUESTED}")

    elif ask.lower() == "query a topic":
        # Input code to point to functions to find images that are close to or match the topic
        print("querying topic")

if __name__ == "__main__":
    get_cli_command()