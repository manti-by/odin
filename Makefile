run:
	uv run manage.py runserver

migrate:
	uv run manage.py migrate

migrations:
	uv run manage.py makemigrations

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
	pre-commit autoupdate

ci: pip check django-checks test
