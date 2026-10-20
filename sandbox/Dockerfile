# Image for the agent's sandbox (see docs/m5_sandbox_taskgen_design.md). Build: miniagent-eval sandbox-build
# pytest is pinned to the version on the host so grading behaves the same inside and outside the container.
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest==9.1.1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /work
