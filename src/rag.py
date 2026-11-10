"""
rag.py — Build and search the RAG knowledge base (Pinecone).
Build: python -m src.rag build
Test:  python -m src.rag test
"""
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

CORPUS_DIR = Path("corpus")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "unioptt-corpus")
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536       # text-embedding-3-small makes vectors with 1536 numbers
CHUNK_SIZE = 1200      # characters per chunk (about 300 tokens)
CHUNK_OVERLAP = 200    # characters repeated between neighbouring chunks
MIN_CHUNK = 100        # drop tiny leftovers


# ---------- 1. Read and clean ----------

def read_doc(path: Path) -> tuple[dict, str]:
    """Split a corpus file into its header (metadata) and body (page text)."""
    raw = path.read_text(encoding="utf-8")
    _, header, body = raw.split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in header.strip().splitlines())
    return meta, body


def clean_text(body: str) -> str:
    """Remove Jina's preamble, images, menus and link clutter."""
    if "Markdown Content:" in body:
        body = body.split("Markdown Content:", 1)[1]
    lines = []
    for line in body.splitlines():
        s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line.strip())        # images
        plain = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)            # [text](url) -> text
        if s != plain and len(plain.strip(" *-#|")) < 25:
            continue                                                  # short menu link
        lines.append(plain)
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk_text(text: str) -> list[str]:
    """Cut text into ~CHUNK_SIZE pieces along paragraph breaks, with overlap."""
    chunks, current = [], ""
    for para in text.split("\n\n"):
        if current and len(current) + len(para) > CHUNK_SIZE:
            chunks.append(current.strip())
            current = current[-CHUNK_OVERLAP:]
        current += "\n\n" + para
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) >= MIN_CHUNK]


# ---------- 2. Embed and store ----------

def embed(texts: list[str]) -> list[list[float]]:
    """Turn texts into vectors with OpenAI."""
    resp = OpenAI().embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def get_index():
    """Connect to the Pinecone index; create it the first time."""
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    if not pc.has_index(INDEX_NAME):
        print(f"Creating Pinecone index '{INDEX_NAME}' (takes ~1 minute)...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return pc.Index(INDEX_NAME)


def build() -> None:
    listed = {s["id"] for s in json.loads((CORPUS_DIR / "sources.json").read_text(encoding="utf-8"))}
    records = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        meta, body = read_doc(path)
        if meta["id"] not in listed:
            print(f"⏭️  {meta['id']:28} skipped (not in sources.json)")
            continue
        chunks = chunk_text(clean_text(body))
        for i, chunk in enumerate(chunks):
            records.append({
                "id": f"{meta['id']}-{i:03d}",
                "text": chunk,
                "metadata": {
                    "source_id": meta["id"],
                    "title": meta["title"],
                    "url": meta["url"],
                    "country": meta["country"],
                    "topic": meta["topic"],
                    "publisher": meta["publisher"],
                    "retrieved": meta["retrieved"],
                    "text": chunk,
                },
            })
        print(f"📄 {meta['id']:28} {len(chunks):>3} chunks")

    index = get_index()
    for start in range(0, len(records), 100):
        batch = records[start:start + 100]
        vectors = embed([r["text"] for r in batch])
        index.upsert(vectors=[
            {"id": r["id"], "values": v, "metadata": r["metadata"]}
            for r, v in zip(batch, vectors)
        ])
    print(f"\n✅ Uploaded {len(records)} chunks to Pinecone index '{INDEX_NAME}'")


# ---------- 3. Search ----------

def search(question: str, country: str | None = None, topic: str | None = None,
           top_k: int = 4) -> list[dict]:
    """Find the chunks closest in meaning to the question, optionally filtered."""
    flt = {}
    if country:
        flt["country"] = {"$eq": country}
    if topic:
        flt["topic"] = {"$eq": topic}
    res = get_index().query(
        vector=embed([question])[0],
        top_k=top_k,
        include_metadata=True,
        filter=flt or None,
    )
    return [
        {
            "score": round(m.score, 3),
            "title": m.metadata["title"],
            "url": m.metadata["url"],
            "country": m.metadata["country"],
            "topic": m.metadata["topic"],
            "text": m.metadata["text"],
        }
        for m in res.matches
    ]


TEST_QUESTIONS = [
    ("Can a student with a Turkish high school diploma go directly to a German university, "
     "or do they need a Studienkolleg?", "DE", None),
    ("How much money must an international student show for a German student visa?", "DE", "costs"),
    ("How much tuition do non-EU students pay for a bachelor's programme in the Netherlands?", "NL", "costs"),
    ("How is a foreign university degree recognised in Türkiye, and what does it cost?", "TR", None),
]


def test() -> None:
    for question, country, topic in TEST_QUESTIONS:
        print(f"\n❓ {question}  [country={country}, topic={topic}]")
        for hit in search(question, country=country, topic=topic, top_k=3):
            snippet = hit["text"][:200].replace("\n", " ")
            print(f"   {hit['score']}  {hit['title']}  ({hit['url']})\n         {snippet}...")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "build":
        build()
    elif command == "test":
        test()
    else:
        print("Usage: python -m src.rag build   or   python -m src.rag test")