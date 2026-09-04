from datetime import datetime, timezone

from app.analysis import analyze, post_name, topics_for
from app.models import RawPost
from app.providers import InstaloaderProvider


def test_topic_classification():
    assert topics_for("New clinical research on protein and nutrition") == ["nutrition", "medical-research"]


def test_post_name_is_bounded():
    assert len(post_name("x" * 100, "abc")) == 80


def test_analysis_engagement():
    post = RawPost(shortcode="abc", caption="Mental health and sleep", published_at=datetime.now(timezone.utc), likes=10, comments=3, url="https://instagram.com/p/abc/")
    result = analyze("sample", [post], datetime.now(timezone.utc))
    assert result.posts[0].engagement == 13
    assert result.top_topics[0].topic == "mental-health"


def test_optional_instagram_counts_do_not_require_extra_metadata():
    assert InstaloaderProvider._node_count({"edge_liked_by": {"count": 42}}, "edge_liked_by") == 42
    assert InstaloaderProvider._node_count({}, "edge_media_to_comment") == 0
