import re
from collections import defaultdict

from app.models import AccountAnalysis, AnalyzedPost, RawPost, TopicTrend


TOPIC_KEYWORDS: dict[str, set[str]] = {
    "nutrition": {"nutrition", "diet", "protein", "vitamin", "food", "meal", "calorie"},
    "fitness": {"fitness", "workout", "exercise", "training", "gym", "cardio", "strength"},
    "mental-health": {"mental", "anxiety", "stress", "mindfulness", "therapy", "wellbeing", "sleep"},
    "preventive-care": {"prevention", "screening", "vaccine", "checkup", "awareness", "risk"},
    "medical-research": {"study", "research", "trial", "evidence", "clinical", "science", "data"},
    "public-health": {"community", "public", "outbreak", "policy", "population", "epidemic"},
    "skincare": {"skin", "skincare", "dermatology", "acne", "sunscreen", "spf"},
    "women-health": {"pregnancy", "fertility", "menopause", "maternal", "period", "pcos"},
}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", text.lower()))


def topics_for(caption: str) -> list[str]:
    words = _words(caption.replace("#", " "))
    matches = [topic for topic, keywords in TOPIC_KEYWORDS.items() if words & keywords]
    return matches or ["other-health"]


def post_name(caption: str, shortcode: str) -> str:
    clean = re.sub(r"\s+", " ", caption).strip()
    if not clean:
        return f"Instagram post {shortcode}"
    first = re.split(r"(?<=[.!?])\s|\n", clean, maxsplit=1)[0]
    return first[:77] + "..." if len(first) > 80 else first


def analyze(
    username: str,
    raw_posts: list[RawPost],
    fetched_at,
    selection_method: str = "recent",
    scanned_post_count: int | None = None,
) -> AccountAnalysis:
    ordered_posts = (
        raw_posts
        if selection_method == "top_engagement"
        else sorted(raw_posts, key=lambda item: item.published_at, reverse=True)
    )
    posts = [
        AnalyzedPost(
            shortcode=p.shortcode,
            post_name=post_name(p.caption, p.shortcode),
            topics=topics_for(p.caption),
            caption=p.caption,
            published_at=p.published_at,
            likes=p.likes,
            comments=p.comments,
            engagement=p.likes + p.comments,
            is_video=p.is_video,
            url=p.url,
        )
        for p in ordered_posts
    ]

    buckets: dict[str, list[tuple[object, int]]] = defaultdict(list)
    for post in posts:
        for topic in post.topics:
            buckets[topic].append((post.published_at, post.engagement))

    trends = []
    for topic, dated_values in buckets.items():
        values = [value for _, value in sorted(dated_values, reverse=True)]
        split = max(1, len(values) // 2)
        recent = values[:split]
        older = values[split:]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else recent_avg
        momentum = recent_avg / older_avg if older_avg else (1.0 if recent_avg == 0 else 2.0)
        trends.append(
            TopicTrend(
                topic=topic,
                post_count=len(values),
                total_engagement=sum(values),
                average_engagement=round(sum(values) / len(values), 2),
                momentum=round(momentum, 2),
            )
        )
    trends.sort(key=lambda item: (item.total_engagement, item.post_count), reverse=True)
    return AccountAnalysis(
        username=username,
        fetched_at=fetched_at,
        post_count=len(posts),
        selection_method=selection_method,
        scanned_post_count=scanned_post_count if scanned_post_count is not None else len(posts),
        top_topics=trends,
        posts=posts,
    )
