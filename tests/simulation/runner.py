"""Chạy bản ghi 14 ngày. Không mô hình, không mạng, không Supabase."""

import argparse
import asyncio
import sys
from pathlib import Path

from tests.simulation.fortnight import build_fortnight_markdown
from tests.simulation.harness import write_crlf


def main() -> None:
    parser = argparse.ArgumentParser(description="Mô phỏng 14 ngày của compass.")
    parser.add_argument("--write", metavar="PATH")
    args = parser.parse_args()
    text = asyncio.run(build_fortnight_markdown())
    if args.write is None:
        sys.stdout.write(text)
        return
    write_crlf(Path(args.write), text)


if __name__ == "__main__":
    main()
