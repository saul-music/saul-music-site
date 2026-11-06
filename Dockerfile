# Servicio del sitio de SAÚL música. uv fijado, PyPI más el índice propio de la librería de render
# (R1), usuario no root. El token del índice entra como secreto de build (`--secret id=acordia_token`)
# y no queda en ninguna capa de la imagen.
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /usr/local/bin/uv

ENV UV_PYTHON_PREFERENCE=only-system \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=secret,id=acordia_token \
    UV_INDEX_ACORDIA_USERNAME=oauth2accesstoken \
    UV_INDEX_ACORDIA_PASSWORD="$(cat /run/secrets/acordia_token)" \
    uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN --mount=type=secret,id=acordia_token \
    UV_INDEX_ACORDIA_USERNAME=oauth2accesstoken \
    UV_INDEX_ACORDIA_PASSWORD="$(cat /run/secrets/acordia_token)" \
    uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim

RUN useradd --system --uid 10001 --no-create-home musicsite
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER musicsite
ENTRYPOINT ["python", "-m", "musicsite.app"]
