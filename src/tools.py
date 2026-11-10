"""
tools.py — The agent's external tools.
Each tool: checks its input, retries on failure, checks its output.
"""
import os

import httpx
from dotenv import load_dotenv
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()  # reads the keys from .env


class ToolError(Exception):
    """A tool failed after all retries, or returned nothing usable."""


def _get_key(name: str) -> str:
    """Read a key from .env, with a clear message if it is missing."""
    key = os.getenv(name)
    if not key:
        raise ToolError(f"{name} is missing. Add it to your .env file.")
    return key


# ── Tool 1: web search (Tavily) ──────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _tavily_call(query: str, max_results: int) -> dict:
    client = TavilyClient(api_key=_get_key("TAVILY_API_KEY"))
    return client.search(query=query, max_results=max_results)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web. Returns a list of {title, url, snippet}."""
    if not query.strip():
        raise ValueError("Search query is empty.")

    try:
        response = _tavily_call(query, max_results)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Tavily search failed after 3 tries: {e}") from e

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": (r.get("content") or "")[:300],
        }
        for r in response.get("results", [])
        if r.get("url")
    ]
    if not results:
        raise ToolError(f"Tavily returned no results for: {query!r}")
    return results


# ── Tool 2: page reader (Jina Reader) ────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _jina_call(url: str) -> str:
    headers = {"Authorization": f"Bearer {_get_key('JINA_API_KEY')}"}
    response = httpx.get(f"https://r.jina.ai/{url}", headers=headers, timeout=60)
    response.raise_for_status()  # turns HTTP errors (404, 500…) into exceptions
    return response.text


def read_page(url: str, min_chars: int = 500) -> dict:
    """Read a web page as clean text. Returns {url, text, chars}."""
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Not a web address: {url!r}")

    try:
        text = _jina_call(url)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Jina could not read {url} after 3 tries: {e}") from e

    if len(text) < min_chars:
        raise ToolError(f"Page too short ({len(text)} characters), probably blocked or empty: {url}")
    return {"url": url, "text": text, "chars": len(text)}

# ── Tool 3: exchange rate (Frankfurter, ECB data) ────────────────────────────

FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _frankfurter_call(base: str, target: str) -> dict:
    response = httpx.get(FRANKFURTER_URL, params={"base": base, "symbols": target}, timeout=30)
    response.raise_for_status()
    return response.json()


def get_exchange_rate(base: str = "EUR", target: str = "TRY") -> dict:
    """Get the latest ECB reference rate. Returns {base, target, rate, date, source_url}."""
    try:
        data = _frankfurter_call(base, target)
    except Exception as e:
        raise ToolError(f"Frankfurter failed after 3 tries: {e}") from e

    rate = data.get("rates", {}).get(target)
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise ToolError(f"Frankfurter returned no valid {base}->{target} rate: {data}")

    return {
        "base": base,
        "target": target,
        "rate": rate,
        "date": data.get("date"),
        "source_url": f"{FRANKFURTER_URL}?base={base}&symbols={target}",
    }

# ── Quick manual test: python -m src.tools ───────────────────────────────────

if __name__ == "__main__":
    print("Testing the three tools...\n")

    try:
        results = search_web("University of Groningen BSc Artificial Intelligence", max_results=3)
        print(f"✅ Tavily     {len(results)} results, first: {results[0]['url']}")
    except Exception as e:
        print(f"❌ Tavily     {e}")

    try:
        page = read_page("https://www.rug.nl/bachelors/artificial-intelligence?lang=en")
        print(f"✅ Jina       {page['chars']} characters read")
    except Exception as e:
        print(f"❌ Jina       {e}")

    try:
        fx = get_exchange_rate("EUR", "TRY")
        print(f"✅ Frankfurter 1 {fx['base']} = {fx['rate']} {fx['target']} (ECB, {fx['date']})")
    except Exception as e:
        print(f"❌ Frankfurter {e}")