FROM python:3.12-slim

WORKDIR /srv/api
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Least privilege: the API never writes to its own image, so it runs as an unprivileged user while
# the compose file mounts the root filesystem read-only (with a small tmpfs on /tmp). A compromise
# in the app therefore cannot rewrite its own code or leave tooling behind. UID/GID 10001 is picked
# outside the base image's system-user range so it cannot collide with a package's own user.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /srv/api

USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
