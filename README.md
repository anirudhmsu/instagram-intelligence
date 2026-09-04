# Instagram Health Research Ingestion Engine

This project collects posts from configured public Instagram accounts, selects recent or high-engagement posts, stores date-partitioned JSON, creates Word reports, and exposes the archive to Claude Desktop through a read-only MCP server.

## System flow

```text
accounts.yaml → Instagram ingestion → engagement/topic analysis
              → data/ingestion/YYYY-MM-DD/HHMMSS/*.json
              → reports/ingestion/YYYY-MM-DD/HHMMSS/*.docx
              → read-only MCP queries from Claude Desktop
```

The MCP server reads saved JSON only. Claude queries never contact Instagram or consume Instagram requests.

## Important limitations

Instagram does not provide a supported API for unrestricted access to every public account. The included Instaloader adapter is unofficial and may be rate-limited, challenged, or blocked. Use it only when permitted by Instagram's terms, privacy law, and your research policy. Do not bypass checkpoints, access controls, or rate limits. Use an approved API or licensed provider for production-scale collection.

Engagement means `available likes + available comments`. Instagram may omit metrics; unavailable values become zero. Results are not normalized by followers, impressions, or reach.

## Prerequisites

- macOS, Linux, or Windows 10/11
- Python 3.10+
- GNU Make
- An Instagram account authorized to view the target profiles
- Claude Desktop, only for MCP querying

```bash
python3 --version
make --version
```

GNU Make is only required on macOS/Linux. Windows uses the included `project.ps1` PowerShell runner.

## 1. Install the project

```bash
cd instagram-health-research
make setup
```

This creates `.venv`, installs dependencies, and creates `.env` from `.env.example` only when `.env` is missing. It never overwrites an existing `.env`.

## 2. Configure Instagram

Edit `.env`:

```dotenv
INSTAGRAM_PROVIDER=instaloader
INSTAGRAM_LOGIN_USERNAME=your_instagram_login_username
INSTAGRAM_PASSWORD=
INSTAGRAM_SESSION_FILE=PATH_REPORTED_BY_INSTALOADER
CACHE_TTL_SECONDS=900
MAX_POSTS=24
MAX_SCAN_POSTS=200
```

`INSTAGRAM_LOGIN_USERNAME` is the account performing collection—not a target account. Use the absolute session path reported by Instaloader, and keep that machine-local value only in `.env`.

### Recommended session setup: Chrome

Log into Instagram in Chrome, confirm the feed loads, and completely quit Chrome with `Cmd+Q`. Then run:

```bash
source .venv/bin/activate
instaloader --load-cookies chrome
```

For Safari:

```bash
instaloader --load-cookies safari
```

macOS may require temporary Full Disk Access for Terminal to read Safari cookies. Never share browser cookies or the generated session file.

### Alternative interactive login

```bash
source .venv/bin/activate
instaloader --login YOUR_INSTAGRAM_USERNAME
```

Enter passwords and two-factor codes only in the terminal. Complete any Instagram checkpoint in a browser and retry.

`INSTAGRAM_PASSWORD` is an optional first-login fallback, but plaintext storage is discouraged and does not avoid checkpoints. Prefer a session and leave it empty:

```dotenv
INSTAGRAM_PASSWORD=
```

`.env` and session files are ignored by Git. Validate without fetching:

```bash
make check-env
```

Expected: `Configuration ready (provider=instaloader)`.

## 3. Add public target accounts

Edit `accounts.yaml`. Use usernames only—do not include `@`, full URLs, or `?igsi=` parameters.

```yaml
defaults:
  selection: top_engagement
  scan_limit: 100
  limit: 12
  research_query: Which posts and health topics generated the highest user engagement?

accounts:
  - username: default_username_1
    enabled: true
  - username: default_username_2
    enabled: true
  - username: account_to_keep_but_skip
    enabled: false
```

| Field | Meaning |
|---|---|
| `username` | Public profile username |
| `enabled` | Whether ingestion processes it |
| `selection` | `recent` or `top_engagement` |
| `scan_limit` | Candidate posts inspected for top engagement |
| `limit` | Selected posts stored and reported |
| `research_query` | Question recorded in JSON and the report |

Defaults apply to all accounts. Override them per account when needed:

```yaml
- username: example_hospital
  enabled: true
  scan_limit: 50
  limit: 10
```

`scan_limit` is capped by `MAX_SCAN_POSTS`; `limit` is capped by `MAX_POSTS`. Larger scans take longer and create more Instagram traffic.

## 4. Test safely

```bash
make test
```

Tests force demo mode and never contact Instagram.

## 5. Run ingestion

Process every enabled account:

```bash
make ingest
```

Run or retry selected accounts already listed in YAML:

```bash
make ingest ONLY="default_username_1 default_username_2"
```

Accounts run sequentially through one session. One failure is recorded while remaining accounts continue. The command exits nonzero if any account fails.

Outputs use Asia/Kolkata date/time:

```text
data/ingestion/YYYY-MM-DD/HHMMSS/
├── account_one.json
├── account_two.json
└── manifest.json

reports/ingestion/YYYY-MM-DD/HHMMSS/
├── account_one.docx
└── account_two.docx
```

The manifest records timing, provider, successes, errors, generated paths, and `complete`/`partial` status. JSON writes are atomic.

Account JSON includes the question, summary, fetch time, selection method, scan count, topic trends, captions, post IDs, timestamps, metrics, content types, permalinks, and flat dataframe-ready `records`.

### Regenerate a report

Reports are automatic, but an existing JSON can be converted manually:

```bash
.venv/bin/python scripts/generate_instagram_report.py \
  data/ingestion/YYYY-MM-DD/HHMMSS/account.json \
  reports/account-report.docx
```

## 6. Configure Claude Desktop MCP

The MCP server provides read-only access to every valid JSON under `data/ingestion`.

| Capability | Purpose |
|---|---|
| `list_datasets` | Show coverage, dates, scan sizes, and sources |
| `top_posts` | Rank posts with account/topic filters |
| `search_posts` | Search names, captions, and topics |
| `compare_accounts` | Compare saved selections across accounts |
| `get_post` | Retrieve a post by username and shortcode |
| `instagram://catalog` | Dataset-catalog resource |
| `research_profile` | Evidence-grounded research prompt |

On macOS, Claude Desktop reads:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

The recommended setup resolves the current project directory automatically, preserves existing servers, and creates a backup:

```bash
make configure-claude
```

Alternatively, merge this template into the existing `mcpServers` object, replacing `PROJECT_ROOT` with the absolute location of your clone. Claude Desktop requires resolvable executable paths and does not reliably start project-relative virtual environments:

```json
{
  "mcpServers": {
    "instagram-health-research": {
      "command": "PROJECT_ROOT/.venv/bin/python",
      "args": ["PROJECT_ROOT/run_mcp.py"]
    }
  }
}
```

The same content is in `claude_desktop_config.example.json`. Update both absolute paths if the project moves.

Then:

1. Completely quit Claude Desktop.
2. Reopen it.
3. Confirm `instagram-health-research` tools are available.
4. Ask Claude to call `list_datasets` before analysis.

The API and ingestion process do not need to run. Claude launches `run_mcp.py` and reads the archive itself.

Example questions:

- “List available datasets and collection dates.”
- “Show the ten highest-engagement posts with Instagram links.”
- “Which posts discuss thyroid symptoms?”
- “Compare recurring topics across Cytecare and Manipal Hospitals.”
- “Use the research_profile prompt to analyze symptom-led hooks.”

Test MCP manually:

```bash
make mcp-inspect
```

`make mcp` starts the raw stdio server and waits silently for an MCP client. Stop it with `Ctrl+C`; do not type ordinary text into its JSON-RPC stream.

## 7. Optional FastAPI service

Start only the API, without ingestion:

```bash
make serve
```

Open `http://127.0.0.1:8000/docs`.

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/research' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "default_username_1",
    "research_query": "Which posts generated the highest engagement?",
    "limit": 12,
    "selection": "top_engagement",
    "scan_limit": 100,
    "save_json": true
  }'
```

To validate, test, ingest, and then start the API:

```bash
make start
```

Every `make start` performs live ingestion. Use `make serve` when fresh ingestion is unnecessary.

## Command reference

```text
make help        Show commands
make setup       Create venv, install dependencies, ensure .env
make check-env   Validate provider and Instagram session
make test        Run offline tests
make ingest      Ingest all enabled YAML accounts
make serve       Start only FastAPI
make start       Test, ingest, then start FastAPI
make mcp         Start the MCP stdio server manually
make mcp-inspect Open the MCP development inspector
make configure-claude Configure Claude Desktop using this clone's paths
```

## Windows 10/11 complete workflow

Run these commands in PowerShell from the project directory. The Windows runner provides the same setup, testing, ingestion, API, and MCP operations as the Makefile.

### Allow the local PowerShell script

If Windows blocks local scripts, open PowerShell and run this once for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Alternatively, use a one-process bypass without changing the user policy:

```powershell
powershell -ExecutionPolicy Bypass -File .\project.ps1 help
```

### Install and configure

```powershell
cd C:\absolute\path\to\SH
.\project.ps1 setup
```

Edit `.env`:

```dotenv
INSTAGRAM_PROVIDER=instaloader
INSTAGRAM_LOGIN_USERNAME=your_instagram_login_username
INSTAGRAM_PASSWORD=
INSTAGRAM_SESSION_FILE=C:\Users\YOUR_WINDOWS_USER\AppData\Local\Instaloader\session-your_instagram_login_username
CACHE_TTL_SECONDS=900
MAX_POSTS=24
MAX_SCAN_POSTS=200
```

Instaloader normally stores Windows sessions under `%LOCALAPPDATA%\Instaloader`.

Log into Instagram in Chrome, confirm the feed works, and completely close Chrome. Then import cookies:

```powershell
.\.venv\Scripts\Activate.ps1
instaloader --load-cookies chrome
```

Or use interactive login:

```powershell
instaloader --login YOUR_INSTAGRAM_USERNAME
```

Never share the session file, password, or browser cookies. Keep `INSTAGRAM_PASSWORD` empty after a session exists.

Validate and test:

```powershell
.\project.ps1 check-env
.\project.ps1 test
```

### Windows ingestion commands

```powershell
# All enabled accounts
.\project.ps1 ingest

# Only selected accounts from accounts.yaml
.\project.ps1 ingest -Only default_username_1,default_username_2
```

Windows generates the same `data\ingestion\YYYY-MM-DD\HHMMSS` JSON folders and `reports\ingestion\YYYY-MM-DD\HHMMSS` Word-report folders. The included `tzdata` dependency keeps Asia/Kolkata partition dates consistent across platforms.

### Windows API commands

```powershell
# API only
.\project.ps1 serve

# Test, ingest, then API
.\project.ps1 start
```

Open `http://127.0.0.1:8000/docs`.

### Configure Claude Desktop on Windows

Claude Desktop uses:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

After running setup, configure it automatically:

```powershell
.\scripts\windows\configure_claude.ps1
```

The configurator:

- resolves the project to absolute Windows paths;
- creates the Claude directory/configuration when missing;
- preserves existing MCP servers;
- creates a timestamped backup before changing an existing file;
- adds or updates only `instagram-health-research`.

Completely quit and reopen Claude Desktop afterward. A manual template is available in `claude_desktop_config.windows.example.json`.

Test the MCP integration locally:

```powershell
.\project.ps1 mcp-inspect
```

### Windows command reference

```text
.\project.ps1 help                         Show commands
.\project.ps1 setup                        Create venv, install dependencies, ensure .env
.\project.ps1 check-env                    Validate provider and session
.\project.ps1 test                         Run offline tests
.\project.ps1 ingest                       Ingest all enabled accounts
.\project.ps1 ingest -Only account1,account2  Ingest selected accounts
.\project.ps1 serve                        Start FastAPI only
.\project.ps1 start                        Test, ingest, then start FastAPI
.\project.ps1 mcp                          Start MCP stdio manually
.\project.ps1 mcp-inspect                  Open the MCP inspector
```

### Windows troubleshooting

- If `py` is missing, install Python from python.org and enable **Add Python to PATH**.
- If `Activate.ps1` is blocked, use the execution-policy command above. The project runner calls the virtual-environment executable directly and does not require activation.
- If Chrome cookies are not found, verify the correct Instagram account is logged in and fully close Chrome before importing.
- If Claude cannot start MCP, verify `.venv\Scripts\python.exe` exists and rerun `configure_claude.ps1`.
- Paths containing spaces are supported by the PowerShell runner and generated Claude configuration.

## General troubleshooting

### Instagram checkpoint required

Log into Instagram in a browser and complete its security challenge. Prefer browser-cookie import over repeatedly submitting the password.

### Chrome reports no cookies

Confirm the correct account can see its feed in Chrome, quit Chrome with `Cmd+Q`, and rerun `instaloader --load-cookies chrome`.

### Safari reports `Operation not permitted`

Temporarily grant Terminal Full Disk Access under System Settings → Privacy & Security, restart Terminal, retry, and revoke access after saving the session.

### Configuration reports a missing session

Confirm `INSTAGRAM_SESSION_FILE` is an absolute path to an existing file. Never commit or share it.

### Ingestion is partial

Read `manifest.json`, correct the issue, and use `make ingest ONLY="failed_one failed_two"`.

### Claude does not show the MCP server

- Validate `claude_desktop_config.json` as JSON.
- Confirm both configured absolute paths exist.
- Run `make test` and `make mcp-inspect`.
- Completely quit and restart Claude Desktop.

## Production considerations

- Use an approved or licensed collection provider.
- Add a scheduler and persistent queue instead of running ingestion in web workers.
- Add quotas, backoff, structured logging, and monitoring.
- Define public-data retention and deletion policies.
- Store credentials with operating-system secret storage.
- Replace keyword topics with a reviewed health taxonomy or evaluated model.
- Treat captions as untrusted text and distinguish observations from medical claims.
