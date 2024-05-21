.PHONY:build

bash:
	docker exec -it odin-django bash

build:
	docker build -t mantiby/odin:latest .

migrate:
	docker exec -it odin-django python manage.py migrate

static:
	docker exec -it odin-django python manage.py collectstatic --no-input

deploy:
	docker pull mantiby/odin-next:latest
	docker container stop odin-django odin-next odin-worker odin-scheduler
	docker container rm odin-django odin-next odin-worker odin-scheduler
	docker compose up -d

test:
	pytest --create-db --disable-warnings --ds=odin.settings.test odin/

check:
	git add .
	pre-commit run

django-checks:
	python manage.py makemigrations --dry-run --check --verbosity=3 --settings=odin.settings.sqlite
	python manage.py check --fail-level WARNING --settings=odin.settings.sqlite

pip:
	pip install -r requirements.txt

update:
	pcu requirements.txt -u
	pre-commit autoupdate
