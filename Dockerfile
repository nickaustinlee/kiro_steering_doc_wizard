# Multi-stage Dockerfile for testing across Python versions 3.11-3.14
# This Dockerfile uses Poetry for dependency management and testing

# Base stage with Poetry installation
FROM python:3.11-slim as poetry-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# Configure Poetry
RUN poetry config virtualenvs.create false

# Set working directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-root

# Copy source code
COPY . .

# Install the package
RUN poetry install

# Python 3.11 testing stage
FROM poetry-base as test-py311
RUN python --version
CMD ["poetry", "run", "pytest", "-v"]

# Python 3.12 testing stage
FROM python:3.12-slim as test-py312
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install poetry==1.7.1
RUN poetry config virtualenvs.create false
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root
COPY . .
RUN poetry install
RUN python --version
CMD ["poetry", "run", "pytest", "-v"]

# Python 3.13 testing stage
FROM python:3.13-slim as test-py313
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install poetry==1.7.1
RUN poetry config virtualenvs.create false
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root
COPY . .
RUN poetry install
RUN python --version
CMD ["poetry", "run", "pytest", "-v"]

# Default stage (Python 3.11)
FROM test-py311 as default