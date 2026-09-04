import json
from pathlib import Path

from mcp.server import MCPServer

from app.research_store import ResearchStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
store = ResearchStore(PROJECT_ROOT / "data" / "ingestion")
mcp = MCPServer(
    "instagram-health-research",
    title="Instagram Health Research Archive",
    description="Read-only research tools over locally ingested Instagram post datasets.",
    instructions=(
        "Use these tools to answer questions only from saved ingestion JSON. Cite each Instagram "
        "permalink and mention that engagement is available likes plus comments. Comparisons cover "
        "the selected posts in the archive, not complete account histories or reach-normalized metrics."
    ),
)


@mcp.resource("instagram://catalog")
def ingestion_catalog() -> str:
    """Catalog of locally available Instagram ingestion datasets."""
    return json.dumps(store.catalog(), indent=2, ensure_ascii=False)


@mcp.tool()
def list_datasets() -> dict:
    """List available account snapshots with collection dates, scan sizes, and source paths."""
    datasets = store.catalog()
    return {"count": len(datasets), "datasets": datasets}


@mcp.tool()
def top_posts(
    accounts: list[str] | None = None,
    topic: str | None = None,
    limit: int = 10,
) -> dict:
    """Return highest-engagement posts, optionally filtered by account usernames and exact topic."""
    posts = store.top_posts(accounts, topic, limit)
    return {"count": len(posts), "posts": posts, "engagement_definition": "likes + comments when available"}


@mcp.tool()
def search_posts(
    query: str,
    accounts: list[str] | None = None,
    min_engagement: int = 0,
    limit: int = 20,
) -> dict:
    """Search post names, captions, and health topics using keywords and optional account filters."""
    posts = store.search(query, accounts, min_engagement, limit)
    return {"query": query, "count": len(posts), "posts": posts}


@mcp.tool()
def compare_accounts(accounts: list[str] | None = None) -> dict:
    """Compare engagement and leading topics across the selected posts saved for each account."""
    rows = store.compare_accounts(accounts)
    return {
        "accounts": rows,
        "caveat": "Metrics cover deduplicated selected posts in saved datasets, not reach or full histories.",
    }


@mcp.tool()
def get_post(username: str, post_id: str) -> dict:
    """Retrieve one saved post by account username and Instagram shortcode."""
    username = username.lower().lstrip("@")
    for post in store.posts():
        if post.get("username", "").lower() == username and post.get("post_id") == post_id:
            return {"found": True, "post": post}
    return {"found": False, "post": None}


@mcp.prompt()
def research_profile(question: str, accounts: str = "all accounts") -> str:
    """Guide Claude through an evidence-grounded research analysis of the saved archive."""
    return (
        f"Research question: {question}\nAccounts: {accounts}\n"
        "First call list_datasets to establish coverage. Use search_posts and top_posts for evidence, "
        "and compare_accounts only when comparison is relevant. Distinguish observations from inference, "
        "cite Instagram permalinks, quantify engagement, and state dataset limitations."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")

