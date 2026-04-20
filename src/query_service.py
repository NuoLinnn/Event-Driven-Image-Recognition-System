import os
import json
import asyncio
import redis.asyncio as aioredis
from channels import QUERY_REQUESTED, QUERY_ANSWERED

# Connect to REDIS
r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


async def listen():
    pubsub = r.pubsub()
    await pubsub.subscribe(QUERY_REQUESTED)
    print(f'[query_service] Subscribed to {QUERY_REQUESTED}, waiting for messages...')

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
        
            data = json.loads(message["data"])
            if data.get("query"):
                task = asyncio.create_task(run_query_service(data))
                task.add_done_callback(
                    lambda t: t.exception() and print(f"[query_service] task failed: {t.exception()}")
                )
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()
 
# TODO implement this function
async def run_query_service(data: dict):
    """function to run the user requested query"""
    print(f"[query_service] running user query: {data.get('query')}")

    # mock answer
    answer = {"answer" : "[query_service] done with answer!"}
    await send_query_answered_message(answer)


async def send_query_answered_message(answer: str):
    """publish to QUERY_ANSWERED channel after succesfully answering the query"""
    payload = json.dumps(answer)
    await r.publish(QUERY_ANSWERED, payload)
    print(f"[query_service] Sent message to {QUERY_ANSWERED}")