# LC-0 code environment: used for BOTH the agent sandbox and the evaluator.
#
# Build (bootstrap.sh does this for you):
#   docker build -t lc0-env:1 -f docker/Dockerfile docker/
#   If your Docker daemon has no bridge network (e.g. dockerd --bridge=none), add: --network host
# Verify:
#   docker run --rm --network none lc0-env:1 python -m pytest --version   # -> pytest 8.3.3
#
# Base image pinned by digest (python:3.12-slim multi-arch index digest, resolved 2026-11-12).
# No apt-get and no "|| true": every build step must succeed or the build fails.
# Test deps are installed from wheels with --require-hashes (see requirements-env.txt).
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
COPY requirements-env.txt /tmp/requirements-env.txt
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r /tmp/requirements-env.txt \
 && pip check \
 && rm /tmp/requirements-env.txt
ENV PYTHONDONTWRITEBYTECODE=1 PAGER=cat
LABEL org.lc0.component="code-env" org.lc0.version="1"
WORKDIR /repo
