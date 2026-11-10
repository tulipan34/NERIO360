FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --only-binary=:all: -r requirements.txt \
    && groupadd --system appuser && useradd --system --gid appuser --home-dir /app appuser
COPY --chown=appuser:appuser app.py /app/app.py
COPY --chown=appuser:appuser templates /app/templates
COPY --chown=appuser:appuser static /app/static
RUN mkdir -p /app/static/uploads && chown -R appuser:appuser /app/static/uploads
USER appuser
EXPOSE 8000
CMD ["gunicorn","--bind","0.0.0.0:8000","--workers","2","--access-logfile","-","app:app"]
