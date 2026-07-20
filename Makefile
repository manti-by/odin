frontend:
	bun install --cwd frontend && bun run --cwd frontend build

.PHONY: run shell migrate migrations messages locale static deploy test full-test check django-checks install update ci dump restore agent-instance wiki-dedup wiki-consistency frontend

run:
	uv run manage.py runserver

shell:
	uv run manage.py shell

migrate:
	uv run manage.py migrate

migrations:
	uv run manage.py makemigrations

messages:
	uv run manage.py makemessages -l ru

locale:
	uv run manage.py compilemessages -l ru

static:
	uv run manage.py collectstatic --no-input

deploy:
	git pull
	uv sync
	make frontend
	uv run manage.py migrate
	uv run manage.py collectstatic --no-input
	sudo systemctl daemon-reload
	sudo systemctl restart worker.service
	sudo systemctl restart gunicorn.service
	sudo systemctl restart scheduler.service
	sudo systemctl restart sensor-consumer.service
	sudo service nginx reload

test:
	uv run pytest -m "not views" --disable-warnings --ds=odin.settings.test odin/

full-test:
	uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/

check:
	git add .
	uv run ty check
	uv run pre-commit run

django-checks:
	uv run manage.py makemigrations --dry-run --check --verbosity=3 --settings=odin.settings.sqlite
	uv run manage.py check --fail-level WARNING --settings=odin.settings.sqlite

install:
	uv sync --all-extras --dev

update:
	uv run uv-bump
	uv sync --all-extras --dev
	uv run pre-commit autoupdate

ci: install check django-checks full-test

dump:
	pg_dump -h localhost -U odin -d odin > odin.sql

restore:
	psql -h localhost -U odin -d postgres -c "DROP DATABASE odin;"
	psql -h localhost -U odin -d postgres -c "CREATE DATABASE odin;"
	psql -h localhost -U odin -d odin < odin.sql

agent-instance:
	git worktree add $(CURDIR)-$(NAME)
	cp .env $(CURDIR)-$(NAME)/.env

wiki-dedup:
	opencode run /wiki-dedup

wiki-consistency:
	opencode run /wiki-consistency
