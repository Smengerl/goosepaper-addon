# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Supervisor's builder always passes these as build args, whether or not build.yaml exists.
# BUILD_FROM is unused - the base image above is hardcoded, not templated - since this add-on
# only ever targets one arch (see config.yaml).
ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="addon" \
    io.hass.arch="${BUILD_ARCH}"

# WeasyPrint dlopen's Pango/Cairo/GLib at runtime via cffi - no compiler needed, just the shared
# libs. fonts-* gives it something to actually typeset with; ca-certificates is for the RSS/
# reMarkable-API HTTPS requests deliver.py makes; git is needed by uv to fetch the goosepaper
# dependency, which pyproject.toml points at https://github.com/Smengerl/goosepaper-logicpuzzles.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
        fonts-liberation \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /build/goosepaper-addon
COPY . .

# --frozen: build against the exact goosepaper commit pinned in uv.lock, not whatever mainline
# has moved to since - re-run `uv lock` locally and commit the result to pick up fork updates.
RUN uv sync --no-dev --frozen

# HOME controls where remarkapy stores its reMarkable auth token (~/.rmapi by default) - pointed
# at /data so pairing (see README: `remarkapy init`) only has to happen once, on the host volume,
# not on every container recreation.
ENV HOME=/data \
    ADDON_CONFIG=/config/addon_config.json \
    OUTPUT_DIR=/data/output \
    PATH="/build/goosepaper-addon/.venv/bin:${PATH}"

VOLUME ["/config", "/data"]

ENTRYPOINT ["python", "scheduler.py"]
