from datetime import datetime

from pydantic import BaseModel, Field


class RawPost(BaseModel):
    shortcode: str
    caption: str = ""
    published_at: datetime
    likes: int = 0
    comments: int = 0
    is_video: bool = False
    url: str


class AnalyzedPost(BaseModel):
    shortcode: str
    post_name: str
    topics: list[str]
    caption: str
    published_at: datetime
    likes: int
    comments: int
    engagement: int
    is_video: bool
    url: str


class TopicTrend(BaseModel):
    topic: str
    post_count: int
    total_engagement: int
    average_engagement: float
    momentum: float = Field(description="Recent-vs-older engagement ratio; above 1 is accelerating")


class AccountAnalysis(BaseModel):
    username: str
    fetched_at: datetime
    post_count: int
    selection_method: str = "recent"
    scanned_post_count: int = 0
    top_topics: list[TopicTrend]
    posts: list[AnalyzedPost]


class ResearchRequest(BaseModel):
    username: str = Field(description="Public Instagram profile, with or without @")
    research_query: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=12, ge=1, le=50)
    selection: str = Field(default="recent", pattern="^(recent|top_engagement)$")
    scan_limit: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Candidate posts inspected when selection is top_engagement",
    )
    refresh: bool = False
    save_json: bool = True


class ResearchResult(BaseModel):
    research_query: str | None
    summary: str
    analysis: AccountAnalysis
    records: list[dict]
    export_id: str | None = None
    export_url: str | None = None
