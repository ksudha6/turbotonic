.PHONY: up down test test-backend test-browser db-up db-down db-reset seed

db-up:
	docker compose up -d
	@echo "Waiting for Postgres to be healthy..."
	@until docker compose exec postgres pg_isready -U turbo_tonic -d turbo_tonic > /dev/null 2>&1; do sleep 1; done
	@echo "Postgres is ready."

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d
	@echo "Waiting for Postgres to be healthy..."
	@until docker compose exec postgres pg_isready -U turbo_tonic -d turbo_tonic > /dev/null 2>&1; do sleep 1; done
	@echo "Postgres is ready."

seed:
	mkdir -p logs
	uv run python -m backend.src.seed 2>&1 | tee logs/seed.log

up: db-up seed
	mkdir -p logs
	@trap 'kill 0' EXIT; \
	uv run uvicorn backend.src.main:app --host 0.0.0.0 --port 8001 --reload 2>&1 | tee logs/uvicorn.log & \
	cd frontend && npm run dev -- --port 5174 2>&1 | tee ../logs/sveltekit.log & \
	wait

down:
	-pkill -f "uvicorn backend.src.main:app.*8001" 2>/dev/null || true
	-pkill -f "vite" 2>/dev/null || true

test: test-backend test-browser

test-backend:
	mkdir -p logs
	uv run pytest backend/tests/ 2>&1 | tee logs/pytest.log

test-browser:
	mkdir -p logs
	cd frontend && npx playwright test 2>&1 | tee ../logs/playwright-test-browser.log
