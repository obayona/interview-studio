# ruff: noqa: N999

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from backend.report_engine import EvaluationContext, ReportEngine


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Generate an interview report from an evaluation-context JSON file"
    )
    command.add_argument("context", type=Path, help="Path to EvaluationContext JSON")
    command.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    command.add_argument("--model", default="gpt-4.1-mini")
    return command


async def run() -> None:
    command = parser()
    args = command.parse_args()
    if not args.api_key:
        command.error("provide --api-key or OPENAI_API_KEY for this development CLI")
    context = EvaluationContext.model_validate_json(args.context.read_text(encoding="utf-8"))
    report = await ReportEngine.from_openai(args.api_key, args.model).evaluate(context)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(run())
