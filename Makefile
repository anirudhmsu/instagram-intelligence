PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help setup ensure-env install check-env test ingest serve mcp mcp-inspect configure-claude start

help:
	@echo "make setup       Create venv, install dependencies, and ensure .env"
	@echo "make check-env   Validate provider/session configuration"
	@echo "make test        Run the test suite"
	@echo "make ingest      Process all enabled accounts in accounts.yaml"
	@echo "make serve       Start the FastAPI service"
	@echo "make mcp         Start the read-only MCP server over stdio"
	@echo "make mcp-inspect Open the official MCP development inspector"
	@echo "make configure-claude Safely configure Claude Desktop for this clone"
	@echo "make start       Validate, test, ingest, then start the API"

setup: ensure-env install

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)

$(VENV)/.deps-ready: requirements.txt | $(BIN)/python
	$(BIN)/pip install -r requirements.txt
	@touch $(VENV)/.deps-ready

install: $(VENV)/.deps-ready

ensure-env:
	@test -f .env || cp .env.example .env

check-env: ensure-env install
	$(BIN)/python -m scripts.check_env

test: install
	INSTAGRAM_PROVIDER=demo $(BIN)/pytest -q

ingest: check-env
	$(BIN)/python -m app.ingestion --accounts accounts.yaml $(if $(ONLY),--only $(ONLY),)

serve: check-env
	$(BIN)/uvicorn app.main:app --host 0.0.0.0 --port 8000

mcp: install
	$(BIN)/python -m app.mcp_server

mcp-inspect: install
	$(BIN)/mcp dev app/mcp_server.py

configure-claude: install
	$(BIN)/python scripts/configure_claude.py

start: check-env test ingest serve
