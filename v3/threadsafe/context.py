# context.py: Run functions or methods on another core or in another thread

import asyncio
import _thread
from threadsafe import ThreadSafeQueue

# Object describing a job to be run on another core
class Job:
    def __init__(self, func, args, kwargs):
        self.kwargs = kwargs
        self.args = args
        self.func = func
        self.rval = None  # Return value
        self.done = asyncio.ThreadSafeFlag()  # "done" indicator


def worker(q):  # Runs forever on a core executing jobs as they arrive
    while True:
        job = q.get_sync(True)  # Block until a Job arrives
        job.rval = job.func(*job.args, **job.kwargs)
        job.done.set()


class Context:
    def __init__(self, qsize=10):
        self.q = ThreadSafeQueue(qsize)
        _thread.start_new_thread(worker, (self.q,))

    async def assign(self, func, *args, **kwargs):
        job = Job(func, args, kwargs)
        await self.q.put(job)  # Will pause if q is full.
        await job.done.wait()  # Pause until function has run
        return job.rval
