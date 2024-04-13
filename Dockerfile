FROM python:3.12-slim

# Add directories
RUN mkdir -p /srv/app/src/ && \
    mkdir -p /var/lib/app/data/ && \
    mkdir -p /var/lib/app/static/ && \
    mkdir -p /var/lib/app/media/ && \
    mkdir -p /var/log/app/

# Add default user and update permissions
RUN useradd -m -s /bin/bash -d /home/manti manti && \
  chown -R manti:manti /srv/app/src/ /var/lib/app/ /var/log/app/

# Install any needed packages specified in requirements
COPY ../requirements.txt /tmp/requirements.txt
RUN pip install --trusted-host pypi.org --no-cache-dir --upgrade pip && \
    pip install --trusted-host pypi.org --no-cache-dir -r /tmp/requirements.txt

# Run
USER manti
WORKDIR /srv/app/src/
CMD python manage.py runserver
