migrate:
	python manage.py migrate

static:
	python manage.py collectstatic --no-input

deploy:
	git pull
	uv pip install -r requirements.txt
	python manage.py migrate
	python manage.py collectstatic --no-input
	sudo systemctl daemon-reload
	sudo systemctl restart worker.service
	sudo systemctl restart gunicorn.service
	sudo systemctl restart scheduler.service
	sudo service nginx reload

test:
	pytest --create-db --disable-warnings --ds=odin.settings.test odin/

check:
	git add .
	pre-commit run

django-checks:
	python manage.py makemigrations --dry-run --check --verbosity=3 --settings=odin.settings.sqlite
	python manage.py check --fail-level WARNING --settings=odin.settings.sqlite

pip:
	uv pip install -r requirements.txt

update:
	pcu requirements.txt -u
	pre-commit autoupdate
