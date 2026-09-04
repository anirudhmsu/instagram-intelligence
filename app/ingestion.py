import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import ValidationError

from app.config import get_settings
from app.models import ResearchResult
from app.providers import ProviderError, make_provider
from app.services import dataframe_records, select_and_analyze, summarize
from scripts.generate_instagram_report import build_report


USERNAME_PATTERN = re.compile(r"[a-z0-9._]{1,30}")


def load_accounts(path: Path) -> tuple[dict, list[dict]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = payload.get("defaults", {})
    accounts = payload.get("accounts", [])
    if not isinstance(defaults, dict) or not isinstance(accounts, list):
        raise ValueError("accounts.yaml must contain a defaults mapping and accounts list")
    enabled = []
    for entry in accounts:
        if not isinstance(entry, dict) or "username" not in entry:
            raise ValueError("Each account must be a mapping containing username")
        if entry.get("enabled", True):
            enabled.append({**defaults, **entry})
    return defaults, enabled


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def run(
    config_path: Path,
    output_root: Path,
    report_root: Path,
    only: set[str] | None = None,
) -> dict:
    _, accounts = load_accounts(config_path)
    if only:
        accounts = [
            account for account in accounts
            if str(account["username"]).strip().lstrip("@").lower() in only
        ]
    settings = get_settings()
    provider = make_provider(
        settings.instagram_provider,
        settings.instagram_login_username,
        settings.instagram_password.get_secret_value() if settings.instagram_password else None,
        settings.instagram_session_file,
    )
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    date_folder = now.strftime("%Y-%m-%d")
    run_id = now.strftime("%H%M%S")
    data_dir = output_root / date_folder / run_id
    report_dir = report_root / date_folder / run_id
    manifest = {
        "run_id": run_id,
        "started_at": now.isoformat(),
        "provider": settings.instagram_provider,
        "accounts_requested": len(accounts),
        "successes": [],
        "errors": [],
    }

    for entry in accounts:
        username = str(entry["username"]).strip().lstrip("@").lower()
        try:
            if not USERNAME_PATTERN.fullmatch(username):
                raise ValueError("invalid Instagram username")
            selection = str(entry.get("selection", "top_engagement"))
            if selection not in {"recent", "top_engagement"}:
                raise ValueError("selection must be recent or top_engagement")
            limit = min(int(entry.get("limit", 12)), settings.max_posts)
            scan_limit = min(
                max(int(entry.get("scan_limit", 100)), limit), settings.max_scan_posts
            )
            fetch_limit = scan_limit if selection == "top_engagement" else limit
            candidates = provider.fetch_posts(username, fetch_limit)
            analysis = select_and_analyze(username, candidates, limit, selection)
            query = entry.get("research_query")
            result = ResearchResult(
                research_query=query,
                summary=summarize(analysis, query),
                analysis=analysis,
                records=dataframe_records(analysis),
            )
            json_path = data_dir / f"{username}.json"
            report_path = report_dir / f"{username}.docx"
            atomic_json(json_path, result.model_dump(mode="json"))
            if analysis.posts:
                build_report(json_path, report_path)
            manifest["successes"].append({
                "username": username,
                "posts_scanned": analysis.scanned_post_count,
                "posts_saved": analysis.post_count,
                "json": str(json_path),
                "report": str(report_path) if analysis.posts else None,
            })
            print(f"[ok] @{username}: {analysis.post_count} posts -> {json_path}")
        except (ProviderError, ValueError, ValidationError, OSError) as exc:
            manifest["errors"].append({"username": username, "error": str(exc)})
            print(f"[error] @{username}: {exc}", file=sys.stderr)

    manifest["finished_at"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    manifest["status"] = "complete" if not manifest["errors"] else "partial"
    atomic_json(data_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch Instagram ingestion engine")
    parser.add_argument("--accounts", type=Path, default=Path("accounts.yaml"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/ingestion"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/ingestion"))
    parser.add_argument(
        "--only",
        nargs="+",
        help="Process only these usernames from accounts.yaml",
    )
    args = parser.parse_args()
    only = {name.strip().lstrip("@").lower() for name in args.only} if args.only else None
    manifest = run(args.accounts, args.data_dir, args.report_dir, only)
    print(
        f"Run {manifest['run_id']} finished: {len(manifest['successes'])} succeeded, "
        f"{len(manifest['errors'])} failed"
    )
    return 1 if manifest["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
