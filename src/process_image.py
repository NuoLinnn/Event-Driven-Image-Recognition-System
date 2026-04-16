import os
import json
import asyncio
import redis.asyncio as aioredis
from channels import IMAGE_UPLOADED, IMAGE_ANNOTATED, IMAGE_EMBEDDED, IMAGE_PROCESSING_REQUESTED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(*CHANNEL_HANDLERS)
    print(f"[process_image] Subscribed to '{list(CHANNEL_HANDLERS.keys())}', waiting for messages...")
 
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        channel = message["channel"]
        handler = CHANNEL_HANDLERS.get(channel)
            
        if handler:
            asyncio.create_task(handler(data))


async def send_image_processing_requested_message(data: dict):
    payload = json.dumps(data)
    await r.publish(IMAGE_PROCESSING_REQUESTED, payload)
    print(f"[process_image] send message to {IMAGE_PROCESSING_REQUESTED}")


async def process_image(data: dict):
    """funciton to embed the image in the message"""
    print(f"[process_image] processing image: {data.get("image_id")}")

    await send_image_processing_requested_message(data)

async def process_embedded(data: dict):
    print(f"[process_image] Handling processed: {data.get('image_id')}")
    # TODO: your logic here

async def process_annotated(data: dict):
    print(f"[process_image] Handling annotated: {data.get('image_id')}")
    # TODO: your logic here

# list channels this module listens to 
CHANNEL_HANDLERS = {
    IMAGE_UPLOADED: process_image,
    IMAGE_ANNOTATED: process_annotated,
    IMAGE_EMBEDDED: process_embedded,
}



# # Create a function to listen for the upload image to have a value returned
# def process_image_ready(stream_name):
#     last_id = '0'
#     while True:
#         # Make a 5 sec block in the read stream to add new data
#         response = r.xread({stream_name: last_id}, count = 1, block=5000)
        
#         if response:
#             for stream, messages in response:
#                 # Set image processing code here
                


#     # Send information to either the annotation service or the embedding service
#     return
