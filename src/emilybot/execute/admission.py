"""Admission control for JavaScript execution, shared by every request in the bot.

At most `max_active` executions run at once. Up to `max_pending` more wait in FIFO
order, with at most one waiting request per caller. A request that cannot queue, or
waits longer than `pending_timeout`, gets `ExecutorBusy` instead of piling up.
"""

import asyncio
import weakref
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

BUSY_MESSAGE = "⏳ The bot is busy running other code. Try again in a few seconds."


class ExecutorBusy(Exception):
    """Raised when an execution cannot be admitted."""


@dataclass
class _Waiter:
    caller: str
    future: asyncio.Future[None]


@dataclass
class ExecutionAdmission:
    max_active: int = 2
    max_pending: int = 8
    pending_timeout: float = 5.0
    _active: int = 0
    _pending: deque[_Waiter] = field(default_factory=lambda: deque[_Waiter]())

    @asynccontextmanager
    async def slot(self, caller: str) -> AsyncIterator[None]:
        """Hold an execution slot for the duration of the block."""
        await self._acquire(caller)
        try:
            yield
        finally:
            self._release()

    async def _acquire(self, caller: str) -> None:
        if self._active < self.max_active and not self._pending:
            self._active += 1
            return
        if len(self._pending) >= self.max_pending or any(
            w.caller == caller for w in self._pending
        ):
            raise ExecutorBusy()
        waiter = _Waiter(caller, asyncio.get_running_loop().create_future())
        self._pending.append(waiter)
        try:
            await asyncio.wait_for(
                asyncio.shield(waiter.future), timeout=self.pending_timeout
            )
        except BaseException as e:
            if waiter.future.done() and not waiter.future.cancelled():
                # The slot was handed over just as we gave up; pass it on
                self._release()
            else:
                waiter.future.cancel()
                self._pending.remove(waiter)
            if isinstance(e, asyncio.TimeoutError):
                raise ExecutorBusy() from None
            raise

    def _release(self) -> None:
        # Hand the slot directly to the next waiter, so the count never drops
        # below the number of running executions.
        while self._pending:
            waiter = self._pending.popleft()
            if not waiter.future.done():
                waiter.future.set_result(None)
                return
        self._active -= 1


_admissions: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, ExecutionAdmission]" = weakref.WeakKeyDictionary()


def get_admission() -> ExecutionAdmission:
    """The shared admission for the running event loop (the bot runs one loop)."""
    loop = asyncio.get_running_loop()
    admission = _admissions.get(loop)
    if admission is None:
        admission = _admissions[loop] = ExecutionAdmission()
    return admission
