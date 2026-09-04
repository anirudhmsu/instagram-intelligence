import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


class ResearchStore:
    def __init__(self, root: Path):
        self.root = root

    def dataset_paths(self) -> list[Path]:
        return sorted(
            path for path in self.root.glob("*/*/*.json")
            if path.name != "manifest.json"
        )

    def catalog(self) -> list[dict[str, Any]]:
        datasets = []
        for path in self.dataset_paths():
            payload = self._read(path)
            analysis = payload.get("analysis", {})
            datasets.append({
                "account": analysis.get("username", path.stem),
                "fetched_at": analysis.get("fetched_at"),
                "selection_method": analysis.get("selection_method"),
                "posts_scanned": analysis.get("scanned_post_count", 0),
                "posts_available": len(payload.get("records", [])),
                "dataset": str(path.relative_to(self.root)),
            })
        return datasets

    def posts(self, latest_only: bool = True) -> list[dict[str, Any]]:
        snapshots: dict[tuple[str, str], dict[str, Any]] = {}
        archive = []
        for path in self.dataset_paths():
            payload = self._read(path)
            fetched_at = payload.get("analysis", {}).get("fetched_at", "")
            for record in payload.get("records", []):
                post = {**record, "fetched_at": fetched_at, "dataset": str(path.relative_to(self.root))}
                if latest_only:
                    key = (str(post.get("username", "")), str(post.get("post_id", "")))
                    previous = snapshots.get(key)
                    if previous is None or fetched_at > previous.get("fetched_at", ""):
                        snapshots[key] = post
                else:
                    archive.append(post)
        return list(snapshots.values()) if latest_only else archive

    def top_posts(
        self,
        accounts: list[str] | None = None,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        account_filter = {item.lower().lstrip("@") for item in accounts or []}
        matches = []
        for post in self.posts():
            if account_filter and post.get("username", "").lower() not in account_filter:
                continue
            if topic and topic.lower() not in {str(item).lower() for item in post.get("topics", [])}:
                continue
            matches.append(post)
        matches.sort(key=lambda post: (post.get("engagement", 0), post.get("published_at", "")), reverse=True)
        return matches[: max(1, min(limit, 100))]

    def search(
        self,
        query: str,
        accounts: list[str] | None = None,
        min_engagement: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        account_filter = {item.lower().lstrip("@") for item in accounts or []}
        scored = []
        for post in self.posts():
            if account_filter and post.get("username", "").lower() not in account_filter:
                continue
            if int(post.get("engagement", 0)) < min_engagement:
                continue
            title = str(post.get("post_name", "")).lower()
            caption = str(post.get("caption", "")).lower()
            topics = " ".join(post.get("topics", [])).lower()
            score = sum(3 for term in terms if term in topics)
            score += sum(2 for term in terms if term in title)
            score += sum(1 for term in terms if term in caption)
            if not terms or score:
                scored.append((score, int(post.get("engagement", 0)), post))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in scored[: max(1, min(limit, 100))]]

    def compare_accounts(self, accounts: list[str] | None = None) -> list[dict[str, Any]]:
        account_filter = {item.lower().lstrip("@") for item in accounts or []}
        buckets: dict[str, list[dict]] = defaultdict(list)
        for post in self.posts():
            username = post.get("username", "")
            if not account_filter or username.lower() in account_filter:
                buckets[username].append(post)
        comparisons = []
        for username, posts in buckets.items():
            engagements = [int(post.get("engagement", 0)) for post in posts]
            topic_counts: dict[str, int] = defaultdict(int)
            for post in posts:
                for topic in post.get("topics", []):
                    topic_counts[topic] += 1
            comparisons.append({
                "account": username,
                "posts_in_dataset": len(posts),
                "total_engagement": sum(engagements),
                "average_engagement": round(sum(engagements) / len(engagements), 2),
                "highest_engagement": max(engagements),
                "leading_topics": [
                    topic for topic, _ in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:3]
                ],
            })
        comparisons.sort(key=lambda item: item["average_engagement"], reverse=True)
        return comparisons

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

