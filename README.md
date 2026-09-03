# Android Device Quality CI/CD

[![CI](https://github.com/rehansaify/android-device-quality-cicd/actions/workflows/ci.yml/badge.svg)](https://github.com/rehansaify/android-device-quality-cicd/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/Linting-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Pytest](https://img.shields.io/badge/Testing-Pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)
[![Docker](https://img.shields.io/badge/Container-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![GHCR](https://img.shields.io/badge/Registry-GHCR-181717?logo=github&logoColor=white)](https://github.com/features/packages)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Python-based Android device quality simulator with an automated CI/CD pipeline using GitHub Actions, Docker, and GitHub Container Registry.

The project simulates device pre-flight checks such as battery, storage, thermal state, connection, and boot status before allowing an automated test suite to execute.

## Project Overview

In real Android device testing environments, test execution can fail or become unreliable when devices have poor health conditions.

This project implements a deterministic device quality gate that evaluates simulated device telemetry before test execution.

```text
Device Telemetry
       |
       v
+----------------------+
| Device Validation    |
+----------------------+
       |
       v
+----------------------+
| Health Evaluation    |
| Battery              |
| Storage              |
| Temperature          |
| Connection           |
| Boot Status          |
+----------------------+
       |
       v
   Quality Gate
    /       \
   /         \
PASS         CRITICAL
 |              |
 v              v
Run Tests     Block Tests
 |
 v
JSON Report
```

## CI/CD Pipeline

Every pull request and push to `main` is validated through GitHub Actions.

```text
              Pull Request / Push
                       |
                       v
              GitHub Actions
                       |
              +--------+--------+
              |                 |
              v                 v
        Ruff Lint/Format     Pytest
              |                 |
              +--------+--------+
                       |
                 Both Pass?
                       |
                       v
              Docker Buildx
                       |
                GHA Layer Cache
                       |
                       v
                 Build Image
                       |
              Push to GHCR
              (main only)
```

### Pipeline Features

- Pull request validation
- Push-to-`main` CI/CD
- Ruff linting and formatting checks
- Automated Pytest test suite
- JUnit test report artifacts
- Docker Buildx
- GitHub Actions Docker layer caching
- SHA-based Docker image tagging
- `latest` tag for releases on `main`
- GitHub Container Registry publishing
- Secure authentication using `GITHUB_TOKEN`
- Job dependencies preventing Docker publishing when CI fails
- Protected `main` branch requiring CI checks to pass

## Docker Image

Published images are available through GitHub Container Registry:

```text
ghcr.io/rehansaify/android-device-quality-cicd
```

Pull the latest image:

```bash
docker pull ghcr.io/rehansaify/android-device-quality-cicd:latest
```

Run the quality gate:

```bash
docker run --rm ghcr.io/rehansaify/android-device-quality-cicd:latest
```

Example result:

```json
{
  "gate_passed": true,
  "test_suite_executed": true,
  "summary": {
    "gate_status": "PASSED",
    "overall_health": "HEALTHY",
    "tests_total": 4,
    "tests_passed": 4,
    "tests_failed": 0
  }
}
```

Images are also tagged using the short Git commit SHA for traceability:

```text
ghcr.io/rehansaify/android-device-quality-cicd:4b0c187
```

## Device Health Thresholds

| Metric | Healthy | Warning | Critical |
|---|---:|---:|---:|
| Connection | CONNECTED | — | DISCONNECTED / UNAUTHORIZED |
| Boot | BOOTED | — | BOOTING / RECOVERY / OFFLINE |
| Battery | ≥ 20% | 10–19.9% | < 10% |
| Temperature | ≤ 40°C | 40.1–48°C | > 48°C |
| Storage | ≤ 85% | 85.1–95% | > 95% |

A critical condition blocks test execution and causes the quality gate to return exit code `1`.

Warning conditions allow execution to continue while being reported in the health output.

## CLI Usage

Install the project:

```bash
pip install -e .
```

Run a healthy device simulation:

```bash
python -m device_quality --sample
```

Run a warning-level simulation:

```bash
python -m device_quality --sample-warning
```

Run a critical device simulation:

```bash
python -m device_quality --sample-critical
```

Evaluate telemetry from a JSON file:

```bash
python -m device_quality --file device.json
```

Export a quality report:

```bash
python -m device_quality --sample --output reports/gate_report.json
```

## Testing

Run the test suite:

```bash
pytest -v
```

Run linting:

```bash
ruff check .
```

Verify formatting:

```bash
ruff format --check .
```

## Project Structure

```text
android-device-quality-cicd/
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── device_quality/
│       ├── __init__.py
│       ├── __main__.py
│       ├── device.py
│       ├── health.py
│       └── runner.py
├── tests/
│   ├── test_device.py
│   ├── test_health.py
│   └── test_runner.py
├── Dockerfile
├── .dockerignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Technology Stack

- Python 3.12
- Pytest
- Ruff
- Docker
- Docker Buildx
- GitHub Actions
- GitHub Container Registry
- GitHub Actions Cache
- Git

## What This Project Demonstrates

- CI/CD pipeline design
- Automated testing
- Static analysis and code quality enforcement
- Docker containerization
- Container registry automation
- Artifact versioning with Git SHA tags
- Docker layer caching
- Secure CI credentials
- Branch protection and quality gates
- Machine-readable test and quality reports

## License

This project is licensed under the MIT License.
