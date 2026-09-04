from pathlib import Path

from app.config import get_settings


def main() -> int:
    if not Path(".env").is_file():
        print("Missing .env. Run 'make setup' or '.\\project.ps1 setup' on Windows")
        return 1
    settings = get_settings()
    if settings.instagram_provider == "instaloader":
        if not settings.instagram_login_username:
            print("INSTAGRAM_LOGIN_USERNAME is required for instaloader mode")
            return 1
        if not settings.instagram_session_file or not Path(settings.instagram_session_file).is_file():
            print("A valid INSTAGRAM_SESSION_FILE is required for instaloader mode")
            return 1
    print(f"Configuration ready (provider={settings.instagram_provider})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
