import json
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path


def configure(config_path: Path, project_root: Path, windows: bool = False) -> Path | None:
    if windows:
        python = project_root / ".venv" / "Scripts" / "python.exe"
    else:
        python = project_root / ".venv" / "bin" / "python"
    launcher = project_root / "run_mcp.py"
    if not python.is_file():
        raise FileNotFoundError("Virtual environment missing. Run project setup first.")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        backup = config_path.with_name(
            f"{config_path.name}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        shutil.copy2(config_path, backup)
    else:
        config = {}
    servers = config.setdefault("mcpServers", {})
    servers["instagram-health-research"] = {
        "command": str(python.resolve()),
        "args": [str(launcher.resolve())],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return backup


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    windows = platform.system() == "Windows"
    if windows:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA is not defined")
        config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    backup = configure(config_path, project_root, windows)
    if backup:
        print(f"Backup created: {backup}")
    print(f"Claude Desktop configured: {config_path}")
    print("Completely quit and reopen Claude Desktop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
