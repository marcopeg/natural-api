.PHONY: start stop kill test e2e help install clear-logs freeze

# Variables
VENV = venv
PYTHON = $(VENV)/bin/python
PYTEST = $(VENV)/bin/pytest
UVICORN = $(VENV)/bin/uvicorn
PIP = $(VENV)/bin/pip
HOST = 0.0.0.0
PORT = 1337
LOGS_DIR = data/logs

help:
	@echo "NaturalAPI - Available commands:"
	@echo "  make install     - Create venv and install dependencies"
	@echo "  make freeze      - Freeze current dependencies to requirements.txt"
	@echo "  make start       - Start the FastAPI server"
	@echo "  make stop        - Stop the FastAPI server gracefully"
	@echo "  make kill        - Force kill all processes on port $(PORT)"
	@echo "  make clear-logs  - Remove all request logs"
	@echo "  make restart     - Kill server, clear logs, and start fresh"
	@echo "  make test        - Run unit tests"
	@echo "  make e2e         - Run E2E tests"
	@echo "  make all-test    - Run all tests (unit + e2e)"

install:
	@echo "Creating virtual environment..."
	python3.11 -m venv $(VENV)
	@echo "Installing dependencies..."
	$(VENV)/bin/pip install -r requirements.txt
	@echo "Done! Activate with: source $(VENV)/bin/activate"

freeze:
	@echo "Freezing dependencies to requirements.txt..."
	@if [ ! -d "$(VENV)" ]; then \
		echo "Error: Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	$(PIP) freeze > requirements.txt
	@echo "Dependencies frozen to requirements.txt"

start:
	@echo "Starting Codex API server on http://$(HOST):$(PORT)"
	@if lsof -ti:$(PORT) > /dev/null 2>&1; then \
		echo "Error: Port $(PORT) is already in use. Run 'make kill' first."; \
		exit 1; \
	fi
	$(UVICORN) src.main:app --host $(HOST) --port $(PORT)

start-bg:
	@echo "Starting Codex API server in background on http://$(HOST):$(PORT)"
	@if lsof -ti:$(PORT) > /dev/null 2>&1; then \
		echo "Error: Port $(PORT) is already in use. Run 'make kill' first."; \
		exit 1; \
	fi
	$(UVICORN) src.main:app --host $(HOST) --port $(PORT) &
	@sleep 2
	@echo "Server started. PID: $$(lsof -ti:$(PORT))"

stop:
	@echo "Stopping Codex API server..."
	@if lsof -ti:$(PORT) > /dev/null 2>&1; then \
		kill $$(lsof -ti:$(PORT)); \
		echo "Server stopped."; \
	else \
		echo "No server running on port $(PORT)."; \
	fi

kill:
	@echo "Force killing all processes on port $(PORT)..."
	@if lsof -ti:$(PORT) > /dev/null 2>&1; then \
		kill -9 $$(lsof -ti:$(PORT)); \
		echo "Processes killed."; \
	else \
		echo "No processes found on port $(PORT)."; \
	fi

test:
	@echo "Running unit tests..."
	$(PYTEST) tests/test_main.py tests/test_providers.py -v

e2e:
	@echo "Running E2E tests..."
	$(PYTEST) tests/test_e2e.py -v

all-test:
	@echo "Running all tests..."
	$(PYTEST) tests/ -v

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete."

clear-logs:
	@echo "Clearing request logs..."
	@if [ -d "$(LOGS_DIR)" ]; then \
		rm -rf $(LOGS_DIR)/*; \
		echo "Logs cleared from $(LOGS_DIR)"; \
	else \
		echo "Logs directory not found: $(LOGS_DIR)"; \
	fi

restart: kill clear-logs start