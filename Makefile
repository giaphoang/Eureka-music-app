.PHONY: server-up server-down server-logs server-test client-install client-run

server-up:
	docker compose up --build -d

server-down:
	docker compose down

server-logs:
	docker compose logs -f api

server-test:
	docker compose run --rm api pytest -q

client-install:
	cd client && python -m pip install -r requirements.txt

client-run:
	cd client && python -m eureka_client.app
