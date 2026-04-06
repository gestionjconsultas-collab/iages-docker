
import asyncio
import threading
import logging

logger = logging.getLogger(__name__)

class AsyncRunner:
    """
    Helper to run async coroutines in a dedicated background thread with a persistent loop.
    This is necessary for Playwright which requires the object to be used in the same loop
    it was created in, and for Flask synchronous views to call async code without
    creating/closing loops repeatedly (which kills Playwright).
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AsyncRunner, cls).__new__(cls)
                cls._instance._start_worker()
            return cls._instance

    def _start_worker(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AsyncRunnerThread")
        self._thread.start()
        logger.info("AsyncRunner thread started")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"AsyncRunner loop crashed: {e}")

    def run_sync(self, coro):
        """
        Submit a coroutine to the background loop and wait for the result in the current thread.
        Thread-safe.
        """
        if not self._loop or not self._loop.is_running():
            logger.warning("AsyncRunner loop not running, restarting...")
            self._start_worker() # Try to recover
            
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

# Global instance
runner = AsyncRunner()
