import json

from app.research_store import ResearchStore


def _write_dataset(root, date, run, account, posts, fetched_at):
    folder = root / date / run
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{account}.json").write_text(json.dumps({
        "analysis": {"username": account, "fetched_at": fetched_at, "selection_method": "top_engagement", "scanned_post_count": 100},
        "records": posts,
    }))


def test_store_deduplicates_and_queries(tmp_path):
    base = {"username": "clinic", "post_id": "abc", "post_name": "Thyroid symptoms", "caption": "Thyroid health guide", "topics": ["preventive-care"], "published_at": "2026-01-01", "engagement": 100, "permalink": "https://instagram.com/p/abc"}
    _write_dataset(tmp_path, "2026-01-01", "100000", "clinic", [base], "2026-01-01T10:00:00Z")
    _write_dataset(tmp_path, "2026-01-02", "100000", "clinic", [{**base, "engagement": 150}], "2026-01-02T10:00:00Z")
    store = ResearchStore(tmp_path)
    assert len(store.catalog()) == 2
    assert len(store.posts()) == 1
    assert store.top_posts()[0]["engagement"] == 150
    assert store.search("thyroid")[0]["post_id"] == "abc"
    assert store.compare_accounts()[0]["average_engagement"] == 150
