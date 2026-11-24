"""Run from backend/ with ASSISTANT_PROVIDER=db python -m api.jobs.assistant_worker."""

import logging
import multiprocessing
import os
import signal
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from math import ceil
from multiprocessing.connection import Connection
from threading import Event, Thread
from time import monotonic

from dotenv import find_dotenv, load_dotenv

from api.errors import ApiError
from api.jobs.assistant_queue import ATTEMPT_SECONDS, AssistantQueue, Claim, PostgresAssistantQueue
from api.jobs.assistant_runner import AgentResult, get_runner, is_transient
from api.services import assistant

Attempt = tuple[AgentResult, bool]
_logger = logging.getLogger(__name__)


def _attempt_failure(retry: bool) -> Attempt:
    return AgentResult(error_code=assistant.FAILURE_CODE, retryable=retry), retry


def _child(send: Connection, claim: Claim) -> None:
    # Third-party agent diagnostics can contain prompts or completions.
    signal.alarm(ceil(min(ATTEMPT_SECONDS, claim.seconds_left)))
    logging.disable(logging.CRITICAL)
    with send, open(os.devnull, "w") as quiet, redirect_stdout(quiet), redirect_stderr(quiet):
        try:
            queue = PostgresAssistantQueue()
            job = queue.load(claim)
            if job is None:
                send.send(_attempt_failure(False))
                return
            outcome = get_runner().run(job, lambda node: queue.step(claim, node))
        except Exception as error:
            send.send(_attempt_failure(is_transient(error)))
        else:
            send.send((outcome, False))


def run_attempt(claim: Claim, *, target: Callable = _child) -> Attempt:
    budget = min(ATTEMPT_SECONDS, claim.seconds_left)
    if budget <= 0:
        return _attempt_failure(True)
    deadline = monotonic() + budget
    ctx = multiprocessing.get_context("spawn")
    receiver, sender = ctx.Pipe(duplex=False)
    with receiver, sender:
        process = ctx.Process(target=target, args=(sender, claim), daemon=True)
        process.start()
        sender.close()
        try:
            if not receiver.poll(max(0, deadline - monotonic())):
                return _attempt_failure(True)
            try:
                attempt = receiver.recv()
            except EOFError:
                return _attempt_failure(False)
            return attempt if monotonic() <= deadline else _attempt_failure(True)
        finally:
            if process.is_alive():
                process.kill()
            process.join()
            process.close()


def work_once(queue: AssistantQueue, run: Callable[[Claim], Attempt] = run_attempt) -> bool:
    claim = queue.claim()
    if claim is None:
        return False
    try:
        result, retry = run(claim)
    except Exception:
        result, retry = _attempt_failure(False)
    queue.finish(claim, result, retry=retry)
    return True


def _maintain(queue: PostgresAssistantQueue, stop: Event) -> None:
    next_purge = 0.0
    while not stop.is_set():
        try:
            queue.maintain()
            if monotonic() >= next_purge and queue.purge() < 1000:
                next_purge = monotonic() + 60
        except ApiError:
            _logger.warning("assistant worker maintenance unavailable")
        stop.wait(1)


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True), override=False)
    if not assistant.uses_assistant_db():
        raise SystemExit("별도 워커는 ASSISTANT_PROVIDER=db에서 실행합니다.")
    logging.basicConfig(level=logging.INFO)
    queue = PostgresAssistantQueue()
    stop = Event()
    maintenance = Thread(target=_maintain, args=(queue, stop), daemon=True)
    maintenance.start()
    try:
        while True:
            try:
                if not work_once(queue):
                    stop.wait(0.25)
            except ApiError:
                _logger.warning("assistant worker queue unavailable")
                stop.wait(2)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        maintenance.join(timeout=2)


if __name__ == "__main__":
    main()
