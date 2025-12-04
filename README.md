# Odin server core application

Local dashboard for [Coruscant project](https://github.com/manti-by/coruscant).

## About

Odin is a Django based application that provides a local dashboard for the Coruscant project. 

[![Python 3.12](https://img.shields.io/badge/python-3.12-green.svg)](https://www.python.org/downloads/release/python-3111/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![License](https://img.shields.io/badge/license-BSD-blue.svg)](https://raw.githubusercontent.com/manti-by/db-benchmarks/master/LICENSE)

Author: Alexander Chaika <manti.by@gmail.com>

Source link: [https://github.com/manti-by/odin/](https://github.com/manti-by/odin/)

Requirements: Python 3.12, PostgreSQL, Redis.


## Setup
1. Install [Python 3.12](https://www.python.org/downloads/release/python-3120/) and 
[UV tool](https://docs.astral.sh/uv/getting-started/installation/)

2. Clone sources and swith working directory:

    ```shell
    git clone https://github.com/manti-by/odin.git
    cd odin/
    ```

3. Create [a virtual environment](https://docs.astral.sh/uv/pip/environments/#creating-a-virtual-environment) 
for the project:

```shell
uv venv .venv --prompt odin
```

4. Activate virtual environment and sync python packages:

```shell
source .venv/bin/activate/
uv sync --all-extras
```

5. Collect static, run migrations and create superuser:

```shell
uv run python manage.py collectstatic --no-input
uv run python manage.py createsuperuser
uv run python manage.py migrate
```

6. Run development server:

```shell
uv run python manage.py runserver
```
