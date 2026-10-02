"""Admission control and executor limits, exercised through the Python entry point."""

import asyncio
import time
from typing import Any

import pytest

from emilybot.execute.admission import BUSY_MESSAGE, ExecutionAdmission, ExecutorBusy
from emilybot.execute.context import Context, CtxMessage, create_test_user
from emilybot.execute.executor import (
    OUTPUT_MESSAGE,
    TIMEOUT_MESSAGE,
    JavaScriptExecutor,
)


def make_context() -> Context:
    return Context(
        message=CtxMessage(text=".x"),
        reply_to=None,
        user=create_test_user(),
        server=None,
    )


async def run_admitted(
    admission: ExecutionAdmission, caller: str, code: str, timeout: float = 5.0
) -> tuple[bool, str, str | None]:
    """What run_code does: admission first, then a fresh executor."""
    try:
        async with admission.slot(caller):
            return await JavaScriptExecutor(timeout=timeout).execute(
                code, make_context(), []
            )
    except ExecutorBusy:
        return False, BUSY_MESSAGE, None


# --- Admission alone ---


async def test_admission_queues_fifo_and_hands_over_slots():
    admission = ExecutionAdmission(max_active=1, max_pending=2, pending_timeout=5)
    order: list[str] = []
    release = asyncio.Event()

    async def job(caller: str):
        async with admission.slot(caller):
            order.append(caller)
            await release.wait()

    tasks = [asyncio.create_task(job(c)) for c in ["a", "b", "c"]]
    await asyncio.sleep(0.05)
    assert order == ["a"]
    release.set()
    await asyncio.gather(*tasks)
    assert order == ["a", "b", "c"]
    assert admission._active == 0  # pyright: ignore[reportPrivateUsage]


async def test_admission_rejects_full_queue_and_second_pending_per_caller():
    admission = ExecutionAdmission(max_active=1, max_pending=2, pending_timeout=5)
    release = asyncio.Event()

    async def hold(caller: str):
        async with admission.slot(caller):
            await release.wait()

    running = asyncio.create_task(hold("a"))
    await asyncio.sleep(0.01)
    queued = asyncio.create_task(hold("b"))
    await asyncio.sleep(0.01)
    with pytest.raises(ExecutorBusy):
        await hold("b")  # b already waits
    queued2 = asyncio.create_task(hold("c"))
    await asyncio.sleep(0.01)
    with pytest.raises(ExecutorBusy):
        await hold("d")  # queue full
    release.set()
    await asyncio.gather(running, queued, queued2)


async def test_admission_pending_expires_and_cancellation_releases():
    admission = ExecutionAdmission(max_active=1, max_pending=4, pending_timeout=0.2)
    release = asyncio.Event()

    async def hold(caller: str):
        async with admission.slot(caller):
            await release.wait()

    running = asyncio.create_task(hold("a"))
    await asyncio.sleep(0.01)
    with pytest.raises(ExecutorBusy):
        await hold("b")
    cancelled = asyncio.create_task(hold("c"))
    await asyncio.sleep(0.01)
    cancelled.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled
    release.set()
    await running
    assert admission._active == 0  # pyright: ignore[reportPrivateUsage]
    assert not admission._pending  # pyright: ignore[reportPrivateUsage]


# --- Through the executor ---


@pytest.mark.timeout(30)
async def test_burst_of_trivial_jobs_all_complete():
    admission = ExecutionAdmission()
    results = await asyncio.gather(
        *(run_admitted(admission, f"user{i}", f"print({i})") for i in range(10))
    )
    assert [r[:2] for r in results] == [(True, str(i)) for i in range(10)]


@pytest.mark.timeout(30)
async def test_burst_of_infinite_jobs_times_out_two_and_rejects_the_rest():
    admission = ExecutionAdmission()
    start = time.monotonic()
    results = await asyncio.gather(
        *(run_admitted(admission, f"user{i}", "while (true) {}") for i in range(10))
    )
    messages = sorted(r[1] for r in results)
    timeout = TIMEOUT_MESSAGE.format(limit=5.0)
    assert messages == sorted([timeout] * 2 + [BUSY_MESSAGE] * 8)
    assert time.monotonic() - start < 15


@pytest.mark.timeout(15)
async def test_two_second_busy_loop_succeeds():
    ok, _output, value = await JavaScriptExecutor().execute(
        "const end = Date.now() + 2000; while (Date.now() < end) {}; 'done'",
        make_context(),
        [],
    )
    assert (ok, value) == (True, '"done"')


@pytest.mark.timeout(15)
async def test_print_flood_reports_output_limit():
    ok, output, _value = await JavaScriptExecutor().execute(
        'const s = "x".repeat(10000); while (true) print(s)', make_context(), []
    )
    assert (ok, output) == (False, OUTPUT_MESSAGE)


@pytest.mark.timeout(15)
async def test_cancellation_kills_and_reaps_the_child(monkeypatch: pytest.MonkeyPatch):
    processes: list[asyncio.subprocess.Process] = []
    original = asyncio.create_subprocess_exec

    async def recording(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", recording)
    task = asyncio.create_task(
        JavaScriptExecutor(timeout=30).execute("while (true) {}", make_context(), [])
    )
    await asyncio.sleep(1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(processes) == 1
    assert processes[0].returncode is not None
