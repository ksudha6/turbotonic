.PHONY: up down test-backend test-browser

up:
	mkdir -p logs
	@trap 'kill 0' EXIT; \
	uv run uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee logs/uvicorn.log & \
	cd frontend && npm run dev 2>&1 | tee ../logs/sveltekit.log & \
	wait

down:
	-pkill -f "uvicorn backend.src.main:app" 2>/dev/null || true
	-pkill -f "vite" 2>/dev/null || true

test-backend:
	mkdir -p logs
	uv run pytest backend/tests/ 2>&1 | tee logs/pytest.log

test-browser:
	mkdir -p logs
	cd frontend && npx playwright test 2>&1 | tee ../logs/playwright-test-browser.log
