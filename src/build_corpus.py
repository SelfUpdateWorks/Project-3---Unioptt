"""
build_corpus.py — Download the RAG reference pages listed in corpus/sources.json.
Run: python -m src.build_corpus
"""
import json
import time
from datetime import date
from pathlib import Path

from src.tools import ToolError, read_page

CORPUS_DIR = Path("corpus")
SOURCES_FILE = CORPUS_DIR / "sources.json"


def main() -> None:
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    saved, failed = 0, []

    for s in sources:
        try:
            page = read_page(s["url"])
        except (ToolError, ValueError) as e:
            failed.append(s["id"])
            print(f"❌ {s['id']}: {e}")
            continue

        header = (
            "---\n"
            f"id: {s['id']}\n"
            f"title: {s['title']}\n"
            f"url: {s['url']}\n"
            f"country: {s['country']}\n"
            f"topic: {s['topic']}\n"
            f"publisher: {s['publisher']}\n"
            f"retrieved: {date.today().isoformat()}\n"
            "---\n\n"
        )
        (CORPUS_DIR / f"{s['id']}.md").write_text(header + page["text"], encoding="utf-8")
        saved += 1
        print(f"✅ {s['id']:28} {page['chars']:>7} characters")
        time.sleep(1)  # be polite: one page per second

    print(f"\nDone: {saved} saved, {len(failed)} failed {failed if failed else ''}")


if __name__ == "__main__":
    main()