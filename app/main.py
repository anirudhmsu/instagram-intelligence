import re
from pathlib import Path
from uuid import uuid4
from threading import Lock
from time import monotonic

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import get_settings
from app.models import AccountAnalysis, ResearchRequest, ResearchResult
from app.providers import ProviderError, make_provider
from app.services import dataframe_records, select_and_analyze, summarize

app = FastAPI(title="Instagram Health Market Analyzer", version="1.0.0")
_cache: dict[tuple[str, int, str, int], tuple[float, AccountAnalysis]] = {}
_cache_lock = Lock()
_export_dir = Path("data/exports")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/accounts/{username}/analysis", response_model=AccountAnalysis)
def account_analysis(
    username: str,
    limit: int = Query(default=12, ge=1, le=50),
    refresh: bool = False,
    selection: str = Query(default="recent", pattern="^(recent|top_engagement)$"),
    scan_limit: int = Query(default=100, ge=1, le=500),
) -> AccountAnalysis:
    username = username.strip().lstrip("@").lower()
    if not re.fullmatch(r"[a-z0-9._]{1,30}", username):
        raise HTTPException(status_code=422, detail="Invalid Instagram username")

    settings = get_settings()
    limit = min(limit, settings.max_posts)
    scan_limit = min(max(scan_limit, limit), settings.max_scan_posts)
    fetch_limit = scan_limit if selection == "top_engagement" else limit
    key = (username, limit, selection, fetch_limit)
    with _cache_lock:
        cached = _cache.get(key)
    if cached and not refresh and monotonic() - cached[0] < settings.cache_ttl_seconds:
        return cached[1]

    try:
        provider = make_provider(
            settings.instagram_provider,
            settings.instagram_login_username,
            settings.instagram_password.get_secret_value() if settings.instagram_password else None,
            settings.instagram_session_file,
        )
        candidates = provider.fetch_posts(username, fetch_limit)
    except (ProviderError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    result = select_and_analyze(username, candidates, limit, selection)
    with _cache_lock:
        _cache[key] = (monotonic(), result)
    return result


@app.post("/api/v1/research", response_model=ResearchResult)
def research(request: ResearchRequest) -> ResearchResult:
    analysis = account_analysis(
        request.username,
        request.limit,
        request.refresh,
        request.selection,
        request.scan_limit,
    )
    records = dataframe_records(analysis)
    result = ResearchResult(
        research_query=request.research_query,
        summary=summarize(analysis, request.research_query),
        analysis=analysis,
        records=records,
    )
    if request.save_json:
        export_id = uuid4().hex
        _export_dir.mkdir(parents=True, exist_ok=True)
        export_path = _export_dir / f"{export_id}.json"
        result.export_id = export_id
        result.export_url = f"/api/v1/exports/{export_id}"
        export_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


@app.get("/api/v1/exports/{export_id}")
def download_export(export_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", export_id):
        raise HTTPException(status_code=404, detail="Export not found")
    path = _export_dir / f"{export_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path, media_type="application/json", filename=path.name)
