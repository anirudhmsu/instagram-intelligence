from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path

from app.models import RawPost


class ProviderError(RuntimeError):
    pass


class InstagramProvider(ABC):
    @abstractmethod
    def fetch_posts(self, username: str, limit: int) -> list[RawPost]:
        raise NotImplementedError


class DemoProvider(InstagramProvider):
    def fetch_posts(self, username: str, limit: int) -> list[RawPost]:
        now = datetime.now(timezone.utc)
        samples = [
            ("Nutrition myths: what recent research and clinical evidence actually say.", 840, 52),
            ("Five-minute mindfulness exercise for better sleep and lower stress.", 1210, 88),
            ("Strength training and protein: a practical workout guide.", 990, 61),
            ("Why preventive screening and regular checkups matter.", 610, 29),
        ]
        return [
            RawPost(
                shortcode=f"demo{i + 1}", caption=caption,
                published_at=now - timedelta(days=i * 4), likes=likes, comments=comments,
                is_video=i % 2 == 1, url=f"https://www.instagram.com/p/demo{i + 1}/",
            )
            for i, (caption, likes, comments) in enumerate(samples[:limit])
        ]


class InstaloaderProvider(InstagramProvider):
    """Unofficial public-page adapter. Use only where permitted by Instagram's terms and law."""

    def __init__(
        self,
        login_username: str | None = None,
        password: str | None = None,
        session_file: str | None = None,
    ):
        import instaloader

        self.loader = instaloader.Instaloader(
            download_pictures=False, download_videos=False, download_video_thumbnails=False,
            download_geotags=False, download_comments=False, save_metadata=False,
            iphone_support=False,
        )
        try:
            if session_file and Path(session_file).is_file():
                if not login_username:
                    raise ValueError("INSTAGRAM_LOGIN_USERNAME is required with INSTAGRAM_SESSION_FILE")
                self.loader.load_session_from_file(login_username, session_file)
            elif password:
                if not login_username:
                    raise ValueError("INSTAGRAM_LOGIN_USERNAME is required with INSTAGRAM_PASSWORD")
                self.loader.login(login_username, password)
                if session_file:
                    Path(session_file).parent.mkdir(parents=True, exist_ok=True)
                    self.loader.save_session_to_file(session_file)
        except instaloader.exceptions.TwoFactorAuthRequiredException as exc:
            raise ProviderError(
                "Instagram requires two-factor authentication. Create a session with the "
                "Instaloader CLI or import browser cookies, then retry."
            ) from exc
        except instaloader.exceptions.LoginException as exc:
            message = str(exc).lower()
            if "checkpoint required" in message:
                raise ProviderError(
                    "Instagram requires a browser checkpoint. Approve the login in Instagram "
                    "or import an existing browser session, then retry."
                ) from exc
            raise ProviderError("Instagram login failed. Check the account session and retry.") from exc

    def fetch_posts(self, username: str, limit: int) -> list[RawPost]:
        import instaloader

        try:
            # Instaloader 4.14.2's Profile.from_username() calls Instagram's
            # web_profile_info iPhone endpoint, which currently fails for some
            # business profiles due to a deleted category schema. A timeline
            # query only needs the already-validated public username.
            profile = instaloader.Profile(self.loader.context, {"username": username})
            profile._has_full_metadata = True
            result = []
            for post in islice(profile.get_posts(), limit):
                node = getattr(post, "_node", {})
                likes = self._node_count(node, "edge_media_preview_like", "edge_liked_by")
                comments = self._node_count(
                    node, "edge_media_to_parent_comment", "edge_media_to_comment"
                )
                result.append(RawPost(
                    shortcode=post.shortcode,
                    caption=post.caption or "",
                    published_at=post.date_utc.replace(tzinfo=timezone.utc),
                    likes=likes,
                    comments=comments,
                    is_video=post.is_video,
                    url=f"https://www.instagram.com/p/{post.shortcode}/",
                ))
            return result
        except (instaloader.exceptions.InstaloaderException, ConnectionError) as exc:
            raise ProviderError(f"Instagram fetch failed: {exc}") from exc

    @staticmethod
    def _node_count(node: dict, *keys: str) -> int:
        """Read optional engagement counts without requesting extra post metadata."""
        for key in keys:
            value = node.get(key)
            if isinstance(value, dict) and isinstance(value.get("count"), int):
                return value["count"]
        return 0


def make_provider(
    name: str,
    login_username: str | None = None,
    password: str | None = None,
    session_file: str | None = None,
) -> InstagramProvider:
    if name == "demo":
        return DemoProvider()
    if name == "instaloader":
        return InstaloaderProvider(login_username, password, session_file)
    raise ValueError(f"Unknown INSTAGRAM_PROVIDER: {name}")
