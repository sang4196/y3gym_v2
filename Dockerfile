FROM python:3.13.15-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26 AS dependencies
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /build
RUN pip install --no-cache-dir uv==0.12.16
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-editable --no-python-downloads

FROM python:3.13.15-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26
ARG SOURCE_REVISION
ARG SOURCE_FINGERPRINT
ARG QA_RUN_ID=production
ARG QA_OWNER_HASH=production
LABEL org.opencontainers.image.revision=$SOURCE_REVISION \
      org.opencontainers.image.source-fingerprint=$SOURCE_FINGERPRINT \
      com.y3gym.qa.run=$QA_RUN_ID com.y3gym.qa.owner=$QA_OWNER_HASH
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 y3gym && useradd --uid 10001 --gid 10001 --no-create-home y3gym \
    && install -d -o 10001 -g 10001 -m 0700 /var/lib/y3gym/media \
    && install -d -o 10001 -g 10001 -m 0755 /var/lib/y3gym/static
COPY --from=dependencies /opt/venv /opt/venv
COPY backend/config /app/backend/config
COPY backend/news /app/backend/news
COPY backend/manage.py /app/backend/manage.py
COPY deploy/gunicorn.conf.py /app/gunicorn.conf.py
COPY prototype/index.html prototype/styles.css prototype/*.js /app/prototype/
COPY prototype/assets /app/prototype/assets
# Managed QA sources are private0600/0700. Runtime code stays root-owned but
# must be readable by the unprivileged application user in either build context.
RUN chmod -R a+rX /app
WORKDIR /app/backend
USER 10001:10001
STOPSIGNAL SIGTERM
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "config.wsgi:application"]
