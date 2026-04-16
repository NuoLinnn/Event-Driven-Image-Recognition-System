import asyncio
import upload_image
import cli_service

# register all listeners to run concurrently
LISTENERS = [
            upload_image.listen,
            #process_image.listen,
            #annotate_image.listen,
            #embed_image.listen
]


async def run_cli():
    """CLI loop for user inputs"""
    loop = asyncio.get_event_loop()
    while True:
        await cli_service.get_cli_command()
        run_again = await loop.run_in_executor(
            None,
            lambda: input("Do another? (Y/N)").strip().lower()
        )
        if run_again != 'y':
            break


async def main():
    tasks = [asyncio.create_task(listener()) for listener in LISTENERS]
    tasks.append(asyncio.create_task(run_cli()))
 
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("[main] All tasks shut down.")
 
 
if __name__ == "__main__":
    asyncio.run(main())