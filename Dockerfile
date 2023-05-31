FROM python:3.9-slim

RUN apt-get update
RUN apt-get -y install git

# add a non-root user to be used in run time
ENV NONROOT_USER=user \
    NONROOT_UID=1000 \
    NONROOT_GID=1000
RUN groupadd -g ${NONROOT_GID} ${NONROOT_USER}
RUN useradd -u ${NONROOT_UID} -g ${NONROOT_GID} -G users -m -c "" -e "" -l -s /bin/bash ${NONROOT_USER}

ENV PIP_ROOT_USER_ACTION=ignore

RUN pip install -U pip

WORKDIR /app

ENV PYTHONPATH=/app

## install base requirements
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# clean ups and patches for security reasons
RUN pip install -U setuptools
RUN python -m pip uninstall -y pip
RUN apt-get -y remove git
RUN dpkg --remove libcurl3-gnutls

COPY . .

# make sure we have access as non-root user
WORKDIR /app
RUN chown -R ${NONROOT_USER} .
RUN chgrp -R ${NONROOT_USER} .

# prepare for run
WORKDIR /app/$SERVICE_NAME
USER ${NONROOT_USER}
EXPOSE 8000

# If running behind a proxy like Nginx or Traefik add --proxy-headers
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--log-config", "/app/resources/logging.conf", "--log-level", "debug"]
