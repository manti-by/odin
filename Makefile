.PHONY:deploy
CURRENT_DIR = $(shell pwd)

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

deploy:
	scp -r [!.]* odin:/home/manti/www/odin/
	ssh odin "/home/manti/.pyenv/versions/odin/bin/pip install -q -r /home/manti/www/odin/requirements.txt"
	ssh odin "/home/manti/.pyenv/versions/odin/bin/python /home/manti/www/odin/manage.py migrate"
	ssh odin "sudo service nginx restart"
	ssh odin "sudo systemctl daemon-reload"
	ssh odin "sudo service gunicorn restart"
