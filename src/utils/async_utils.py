import asyncio

def get_async_loop() -> asyncio.AbstractEventLoop:
    """
    Returns the current asyncio event loop, creating and setting one if needed.
    Unlike asyncio.get_event_loop(), this never raises RuntimeError on Python
    3.14+ when called from a thread without a current loop.
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
