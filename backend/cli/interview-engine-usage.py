# ruff: noqa: N999

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from collections.abc import AsyncIterator
from uuid import uuid4

from backend.interview_engine import (
    CandidateProfile,
    DifficultyLevel,
    InterviewEngineBuilder,
    InterviewType,
)


async def print_buffered(chunks: AsyncIterator[str]) -> None:
    message = "".join([chunk async for chunk in chunks])
    print(f"\nInterviewer: {message}\n")


async def run() -> None:
    parser = argparse.ArgumentParser(description="Run a text interview in the terminal")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--job", required=True, help="Job listing or role description")
    args = parser.parse_args()
    if not args.api_key:
        parser.error("provide --api-key or OPENAI_API_KEY for this development CLI")

    logging.basicConfig(level=logging.DEBUG)
    engine = (
        InterviewEngineBuilder()
        .set_openai_api(args.api_key)
        .set_model(args.model)
        .set_candidate(CandidateProfile(name="Candidate"))
        .set_job_listing(args.job)
        .set_interview_type(InterviewType.MIXED)
        .set_difficulty(DifficultyLevel.MID)
        .build()
    )
    thread_id = str(uuid4())
    await print_buffered(engine.stream_start(thread_id))

    while True:
        answer = input("You (type /end to finish): ")
        if answer.strip().lower() == "/end":
            await print_buffered(engine.stream_end(thread_id))
            break
        await print_buffered(engine.stream_response(thread_id, answer))
        if (await engine.get_state(thread_id)).get("ended"):
            break


if __name__ == "__main__":
    asyncio.run(run())
