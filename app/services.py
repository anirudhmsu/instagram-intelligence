from datetime import datetime, timezone

from app.analysis import analyze
from app.models import AccountAnalysis, RawPost


def select_and_analyze(
    username: str,
    candidates: list[RawPost],
    limit: int,
    selection: str,
) -> AccountAnalysis:
    if selection == "top_engagement":
        selected = sorted(
            candidates,
            key=lambda post: (post.likes + post.comments, post.published_at),
            reverse=True,
        )[:limit]
    else:
        selected = candidates[:limit]
    return analyze(
        username,
        selected,
        datetime.now(timezone.utc),
        selection_method=selection,
        scanned_post_count=len(candidates),
    )


def summarize(result: AccountAnalysis, query: str | None) -> str:
    if not result.posts:
        return f"No posts were available for @{result.username}."
    leaders = ", ".join(t.topic for t in result.top_topics[:3])
    fastest = max(result.top_topics, key=lambda trend: trend.momentum)
    context = f" For the research question '{query}'," if query else ""
    return (
        f"Analyzed {result.post_count} selected posts from @{result.username}.{context} "
        f"the leading topics by engagement are {leaders}. "
        f"{fastest.topic} has the strongest recent momentum ({fastest.momentum}x)."
    )


def dataframe_records(result: AccountAnalysis) -> list[dict]:
    return [
        {
            "username": result.username,
            "post_id": post.shortcode,
            "post_name": post.post_name,
            "caption": post.caption,
            "topics": post.topics,
            "published_at": post.published_at.isoformat(),
            "likes": post.likes,
            "comments": post.comments,
            "engagement": post.engagement,
            "content_type": "video" if post.is_video else "image_or_carousel",
            "permalink": post.url,
        }
        for post in result.posts
    ]
