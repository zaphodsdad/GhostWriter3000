# GhostWriter 3000 — Makefile
# Usage: make run | make docker | make stop | make clean

.PHONY: run docker stop clean test help

help: ## Show this help
	@echo ""
	@echo "  G H O S T W R I T E R   3 0 0 0"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[33m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""

run: ## Start locally (auto-creates venv, installs deps)
	@./run_server.sh

docker: ## Build and run with Docker Compose
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example — add your API key"; fi
	docker compose up -d --build
	@echo ""
	@echo "GhostWriter 3000 running at http://localhost:8000"

stop: ## Stop Docker container
	docker compose down

clean: ## Remove Docker volumes and venv
	docker compose down -v 2>/dev/null || true
	rm -rf backend/venv

test: ## Run backend tests
	cd backend && source venv/bin/activate && pytest

logs: ## Tail Docker logs
	docker compose logs -f
