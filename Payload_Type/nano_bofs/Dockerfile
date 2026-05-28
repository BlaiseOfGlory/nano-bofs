FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc-mingw-w64-x86-64 \
    gcc-mingw-w64-i686 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /Mythic
RUN python -m pip install --no-cache-dir uv==0.7.21

ENV UV_PROJECT_ENVIRONMENT=/venv
ENV UV_PYTHON_PREFERENCE=only-system

COPY ["Payload_Type/nano_bofs/pyproject.toml", "Payload_Type/nano_bofs/uv.lock", "./"]
RUN uv sync --frozen --no-install-project

COPY ["Payload_Type/nano_bofs/", "./"]
COPY ["templates/", "/opt/nano-bofs-base/templates/"]
COPY ["shared/", "/opt/nano-bofs-base/shared/"]
RUN uv sync --frozen

ENV PATH="/venv/bin:${PATH}"

ENV NANO_BOFS_DEFAULT_BACKEND=local
ENV NANO_BOFS_STATE_DIR=/Mythic/.nano-bofs-state

CMD ["python", "main.py"]
