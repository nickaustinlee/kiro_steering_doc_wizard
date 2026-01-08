#!/bin/bash

# Script to test across multiple Python versions using Docker

set -e

echo "Testing steering-wizard across Python versions..."

echo "Building and testing Python 3.11..."
docker-compose build test-py311
docker-compose run --rm test-py311

echo "Building and testing Python 3.12..."
docker-compose build test-py312
docker-compose run --rm test-py312

echo "Building and testing Python 3.13..."
docker-compose build test-py313
docker-compose run --rm test-py313

echo "All Python version tests completed successfully!"