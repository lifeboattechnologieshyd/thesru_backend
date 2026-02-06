# Define Base Image
FROM python:3.13-slim-bookworm AS base


# ---- Python Build Stage ----
FROM base AS python-build-stage


# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    # dependencies for building Python packages
    build-essential \
    gcc \
    libpq-dev \
    python3-dev


# Copy dependency files
COPY requirements.txt ./
COPY requirements ./requirements

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels  \
    -r requirements.txt


# ---- Alloy Download Stage ----
FROM base AS alloy-download-stage

ARG ALLOY_VERSION=1.11.0
ARG TARGETARCH
ARG BUILDPLATFORM

WORKDIR /tmp

RUN echo "Running on ${BUILDPLATFORM} for ${TARGETARCH}"

RUN apt-get update && apt-get install --no-install-recommends -y \
    curl unzip ca-certificates && \
    curl -LO "https://github.com/grafana/alloy/releases/download/v${ALLOY_VERSION}/alloy-linux-${TARGETARCH}.zip" && \
    unzip alloy-linux-${TARGETARCH}.zip && \
    chmod +x alloy-linux-${TARGETARCH} && \
    mv alloy-linux-${TARGETARCH} alloy


# ---- Final Stage ----
FROM base AS final

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /project/

# copy code
COPY . /project/

# make scripts executable
RUN chmod +x /project/scripts/*

# Install system dependencies required for running
RUN apt-get update && apt-get install --no-install-recommends -y \
    cron \
    # Postgres client Runtime Dependencies
    libpq5 \
    # system monitoring
    procps \
    # cleaning up unused files
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*


# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
    && rm -rf /wheels/

# Copy Grafana Alloy binary from alloy-download-stage
COPY --from=alloy-download-stage /tmp/alloy /usr/local/bin/alloy

# Make alloy binary executable
RUN chmod +x /usr/local/bin/alloy

# Expose port
EXPOSE 8000 12345

# Run the application
CMD ["/project/scripts/start.sh"]
