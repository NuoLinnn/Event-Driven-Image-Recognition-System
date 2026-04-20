import os
import json
import asyncio
import redis.asyncio as aioredis
import tkinter as tk
from tkinter import filedialog
from channels import IMAGE_UPLOAD_REQUESTED, QUERY_REQUESTED, QUERY_ANSWERED
import time


ALLOWED_EXTENSIONS = [
    ("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tiff"),
    ("All files", "*.*")
]

r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


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


async def pick_image_file_async() -> str | None:
    """get image file via async"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, pick_image_file)


async def send_image_upload_requested_message(image_path: str):
    """Publish to IMAGE_UPLOAD_REQUESTED channel."""
    image_id = os.path.splitext(os.path.basename(image_path))[0]
    image_path = os.path.abspath(image_path)
    timestamp = time.time()
 
    payload = json.dumps({
        "image_id": image_id,
        "image_path": image_path,
        "timestamp": timestamp
    })
 
    await r.publish(IMAGE_UPLOAD_REQUESTED, payload)
    print(f"[cli_service] Sent image to {IMAGE_UPLOAD_REQUESTED}")


async def send_query_requested_message(message: str):
    """Publish to QUERY_REQUESTED channel"""
    payload = json.dumps({"query" : message})

    await r.publish(QUERY_REQUESTED, payload)
    print(f'[cli_service] Sent query to {QUERY_REQUESTED}')


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(QUERY_ANSWERED)
    print(f'[cli_service] Subscribed to {QUERY_ANSWERED}, waiting for messages...')

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
        
            data = json.loads(message["data"])
            if data.get("answer"):
                task = asyncio.create_task(print_query_output(data))
                task.add_done_callback(
                    lambda t: t.exception() and print(f"[cli_service] task failed: {t.exception()}")
                )
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()

async def print_query_output(data: str):
    print(f'[cli_service] Recieved answer: {data}')


# Create a function to submit a request from the command line
async def get_cli_command():
    loop = asyncio.get_event_loop()
 
    # input() is blocking — run it in a thread too
    ask = await loop.run_in_executor(
        None,
        lambda: input("What do you want to do: 'upload an image', or 'query a topic'? \n").strip()
    )

    # upload an image
    if ask.lower() == "upload an image":
        image_path = await pick_image_file_async()
 
        if not image_path:
            print("No file selected.")
            return
 
        if not os.path.exists(image_path):
            print(f"ERROR: file not found at {image_path}")
            return
 
        await send_image_upload_requested_message(image_path)
 
    # query the database
    elif ask.lower() == "query a topic":
        query = await loop.run_in_executor(
            None,
            lambda: input("What is your query?\n").strip()
        )

        await send_query_requested_message(query)

    elif ask.lower() == "query a topic":
        print("querying topic")