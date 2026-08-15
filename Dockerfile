FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement /tmp/requirements.txt \
    && python -m pip check


FROM python:3.12-slim AS runtime

ARG TOOLBRIDGE_VERSION=1.1.0
ARG TOOLBRIDGE_UID=10001
ARG TOOLBRIDGE_GID=10001

LABEL org.opencontainers.image.title="ToolBridge MCP Server" \
      org.opencontainers.image.version="$TOOLBRIDGE_VERSION" \
      org.opencontainers.image.description="Production ToolBridge MCP API and dashboard runtime"

ENV HOME=/tmp \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOOLBRIDGE_ENVIRONMENT=production \
    TOOLBRIDGE_HOST=0.0.0.0 \
    TOOLBRIDGE_PORT=8000 \
    TOOLBRIDGE_OPERATIONS__CURRENT_PHASE="Phase 7 - Deployment & v1.0.0 Release"

RUN groupadd --gid "$TOOLBRIDGE_GID" toolbridge \
    && useradd --uid "$TOOLBRIDGE_UID" --gid "$TOOLBRIDGE_GID" --no-create-home --shell /usr/sbin/nologin toolbridge \
    && mkdir -p /app/data/csv \
    && chown -R toolbridge:toolbridge /app

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=toolbridge:toolbridge toolbridge ./toolbridge

USER toolbridge:toolbridge

EXPOSE 8000 8501
VOLUME ["/app/data"]

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

CMD ["python", "-m", "uvicorn", "toolbridge.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
