import json
from pathlib import Path

from app.config import get_settings
from app.ingestion import run


def test_batch_ingestion_creates_partitioned_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_PROVIDER", "demo")
    get_settings.cache_clear()
    accounts = tmp_path / "accounts.yaml"
    accounts.write_text(
        """
defaults:
  selection: top_engagement
  scan_limit: 4
  limit: 2
accounts:
  - username: example_health
    enabled: true
  - username: disabled_account
    enabled: false
""".strip(),
        encoding="utf-8",
    )

    manifest = run(accounts, tmp_path / "data", tmp_path / "reports")

    assert manifest["status"] == "complete"
    assert manifest["accounts_requested"] == 1
    success = manifest["successes"][0]
    json_path = Path(success["json"])
    report_path = Path(success["report"])
    assert json_path.is_file()
    assert report_path.is_file()
    assert len(json.loads(json_path.read_text())["records"]) == 2
    assert (json_path.parent / "manifest.json").is_file()
    get_settings.cache_clear()
