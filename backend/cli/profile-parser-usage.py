# ruff: noqa: N999

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from backend.profile_parser import CVParser, PDFTextExtractor


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Extract a structured profile from a CV")
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument("--pdf", type=Path, help="Path to a text-based PDF CV")
    source.add_argument("--text", type=Path, help="Path to an extracted plain-text CV")
    command.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    command.add_argument("--model", default="gpt-4.1-mini")
    return command


async def run() -> None:
    command = parser()
    args = command.parse_args()
    if not args.api_key:
        command.error("provide --api-key or OPENAI_API_KEY for this development CLI")
    text = (
        PDFTextExtractor().extract(args.pdf.read_bytes())
        if args.pdf is not None
        else args.text.read_text(encoding="utf-8")
    )
    suggestions = await CVParser.from_openai(args.api_key, args.model).parse(text)
    print(suggestions.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(run())
