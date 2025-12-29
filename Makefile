run:
	uv run manage.py runserver

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
	uv run manage.py migrate
	uv run manage.py collectstatic --no-input
	sudo systemctl daemon-reload
	sudo systemctl restart worker.service
	sudo systemctl restart gunicorn.service
	sudo systemctl restart scheduler.service
	sudo service nginx reload

test:
	uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/

check:
	git add .
	uv run pre-commit run

django-checks:
	uv run manage.py makemigrations --dry-run --check --verbosity=3 --settings=odin.settings.sqlite
	uv run manage.py check --fail-level WARNING --settings=odin.settings.sqlite

pip:
	uv sync

update:
	uv sync --upgrade
	uv run pre-commit autoupdate

ci: pip check django-checks test

dump:
	pg_dump -h localhost -U odin -d odin > odin.sql

restore:
	psql -h localhost -U odin -d postgres -c "DROP DATABASE odin;"
	psql -h localhost -U odin -d postgres -c "CREATE DATABASE odin;"
	psql -h localhost -U odin -d odin < odin.sql