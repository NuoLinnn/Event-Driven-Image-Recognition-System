import asyncio
import upload_image
import cli_service
import embed_image
import annotate_image
import process_image
import query_service

# register all listeners to run concurrently
LISTENERS = [
            upload_image.listen,
            process_image.listen,
            annotate_image.listen,
            embed_image.listen,
            query_service.listen,
            cli_service.listen
]


async def run_cli():
    """CLI loop for user inputs"""
    loop = asyncio.get_event_loop()
    while True:
        await cli_service.get_cli_command()
        run_again = await loop.run_in_executor(
            None,
            lambda: input("Run another command? (Y/N)\n").strip().lower()
        )
        if run_again != 'y':
            print("Shutting down...")
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()
            return  


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
        print(f"[main] All tasks shut down.")
 
 
if __name__ == "__main__":
    asyncio.run(main())