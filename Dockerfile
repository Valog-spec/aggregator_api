FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /app

RUN chown appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

RUN uv sync --frozen --no-cache --no-dev

ENV UV_NO_CACHE=1
ENV UV_NO_SYNC=1

CMD ["bash", "./run.sh"]
