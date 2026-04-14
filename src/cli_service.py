import os
import json
import redis
from channels import IMAGE_UPLOAD_REQUESTED
import upload_image

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Create a function to submit a request from the command line
def get_cli_command():
    ask = input("What do you want to do: 'upload an image', or 'query a topic'?")
    if ask.lower() == "upload an image":
        # Input code to point to functions to upload and process image
        # Send information to the upload_image service
        image_path = input("enter path to image file:").strip()

        # return if file not found
        if not os.path.exists(image_path):
            print(f"ERROR: file not found at {image_path}")
            return

        # else send payload to IMAGE_UPLOAD_REQUESTED
        payload = json.dumps({"image_path" : os.path.abspath(image_path)})
        r.publish(IMAGE_UPLOAD_REQUESTED, payload)
        print("send image to {IMAGE_UPLOAD_REQUESTED}")

    elif ask.lower() == "query a topic":
        # Input code to point to functions to find images that are close to or match the topic
        print("querying topic")

if __name__ == "__main__":
    get_cli_command()