import json

from scripts.configure_claude import configure


def test_claude_configurator_preserves_servers_and_resolves_paths(tmp_path):
    project = tmp_path / "project"
    python = project / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()
    (project / "run_mcp.py").touch()
    config = tmp_path / "Claude" / "claude_desktop_config.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"mcpServers": {"existing": {"command": "existing"}}}))

    backup = configure(config, project)
    payload = json.loads(config.read_text())

    assert backup and backup.is_file()
    assert "existing" in payload["mcpServers"]
    server = payload["mcpServers"]["instagram-health-research"]
    assert server["command"] == str(python.resolve())
    assert server["args"] == [str((project / "run_mcp.py").resolve())]
