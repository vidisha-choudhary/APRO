# APRO — Adaptive Payment Recovery Orchestrator

Adaptive Payment Recovery Orchestrator (APRO) is designed to intelligently recover failed payments by analyzing failure reasons, executing policy-guarded recovery actions, and optimizing economic recovery value.

## Project Status

**Phase 00 — Engineering Foundation (Complete)**
The project currently has a clean engineering structure, centralized configuration loading, `/health` endpoint, development Docker container, and code-quality tools configured.

The following components are **not** implemented in this phase and will be introduced in future phases:
- Database infrastructure
- Razorpay integration
- Payment recovery logic
- Machine learning models / AI agents
- Policy & safety engine

## Prerequisites

- **Python**: Version 3.11.x (minimum 3.11)
- **Docker**: (Optional) For containerized development

## Installation

We recommend using a Python virtual environment to manage dependencies locally:

1. Clone or navigate to the repository directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows (PowerShell/Cmd)
   # source .venv/bin/activate # macOS/Linux
   ```
3. Install package and development tools in editable mode:
   ```bash
   pip install -e .[dev]
   ```
   *Note: This command installs the primary dependencies as well as development tools specified in `pyproject.toml`.*

## Environment Configuration

Configure application parameters using environment variables or a local `.env` file in the project root.

Copy the example template to get started:
```bash
cp .env.example .env
```

Key configuration variables (see `.env.example` for details):
- `APP_ENV`: Application environment (default: `development`)
- `APP_HOST`: Host address (default: `127.0.0.1`)
- `APP_PORT`: Application port (default: `8000`)
- `LOG_LEVEL`: Logger verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

## Local Startup

Start the local development server:

```bash
uvicorn apro.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, you can access:
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Containerized Execution

You can build and run the development environment in Docker:

```bash
# Build the image
docker build -t apro-app .

# Run the container
docker run -p 8000:8000 --env-file .env.example apro-app
```

## Quality Assurance & Testing

All verification tools are configured to run from the root directory.

### Running Tests

Execute the test suite using `pytest`:

```bash
pytest
```

### Code Formatting

Verify and format python code using `ruff`:

```bash
# Check formatting
ruff format --check .

# Auto-format files
ruff format .
```

### Linting

Check for style and programming errors using `ruff`:

```bash
# Lint checks
ruff check .

# Auto-fix fixable issues
ruff check --fix .
```

### Static Type Checking

Perform static type analysis using `mypy`:

```bash
mypy src
```
