PYTHON ?= python

.PHONY: \
	server-up server-down server-logs server-test \
	client-install client-run client-test \
	dev-install lint type-check test quality api-docs

server-up:
	docker compose up --build -d

server-down:
	docker compose down

server-logs:
	docker compose logs -f api

server-test:
	docker compose run --rm api python -m pytest -q

client-install:
	cd client && python -m pip install -r requirements.txt

client-run:
	cd client && python -m eureka_client.app

client-test:
	cd client && $(PYTHON) -m pytest -q

dev-install:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check client server

type-check:
	$(PYTHON) -m mypy

test: client-test server-test

quality: lint type-check test

api-docs:
	cd server && $(PYTHON) -m scripts.export_openapi --output openapi.json
