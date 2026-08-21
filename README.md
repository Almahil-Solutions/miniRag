# mini-RAG
This is a minimal implementation of the RAG model for question answering.


# Requirements
- python 3.10 or higher

### Install postgresql from apt:
```bash
sudo apt update
sudo apt install libpq-dev gcc python3-dev
```

### Install python using conda
1) Download and install MiniConda from [here](https://www.anaconda.com/docs/getting-started/miniconda/install)
2) Create a new environment with the following command:
```bash
conda create -n mini-rag python=3.10
```
3) Activate the environment:
```bash
conda activate mini-rag
```
### (Optional) Setup you command line interface for better readability

```bash
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$"
```
# Installation

### Install the required packages:
```bash
pip install -r requirements.txt
```
### Setup environment variables
The environment configuration templates are located in the `docker/env` directory.
1) Copy the example templates to create your real `.env` files:
```bash
# E.g., for local development
cp docker/env/.env.Example.fastapi-app src/.env
```
2) Open your new `.env` files and replace all `<CHANGE_ME>` values with secure secrets. 
*Note: The application will refuse to start if it detects default placeholders.*

### Setup docker
For full deployment instructions using Docker, please refer to the detailed guide in [docker/README.md](docker/README.md).

1) Prepare your environment files and `alembic.ini` as described in `docker/README.md`.
2) Run the docker container from the `docker` directory:
```bash
cd docker
docker compose up -d
```

### Run the FastAPI server
```bash
uvicorn main:app --reload --host 0.0.0.0  --port 5000 
```


# Celery (Development Mode)

For development, you can run Celery services manually instead of using Docker:

To Run the **Celery worker**, you need to run the following command in a separate terminal:

```bash
$ python -m celery -A celery_app worker --queues=default,file_processing,data_indexing --loglevel=info
```

To run the **Beat scheduler**, you can run the following command in a separate terminal:

```bash
$ python -m celery -A celery_app beat --loglevel=info
```

To Run **Flower Dashboard**, you can run the following command in a separate terminal:

```bash
$ python -m celery -A celery_app flower --conf=flowerconfig.py
```

Open your browser and navigate to `http://localhost:5555` to view the dashboard (HTTP Basic Auth required).


---

## Running Tests & Quality Checks

Install development and test dependencies:

```bash
pip install -r requirements-dev.txt
```

Run test suite with coverage:

```bash
cd src
python -m pytest tests/ --cov=. --cov-report=term-missing -v
```

Run linting and static type checking:

```bash
ruff check src/
mypy src/ --ignore-missing-imports
```


---

## API Design & Versioning Policy

### API Versioning
- **Current Version:** All production endpoints are rooted under the `/api/v1/` prefix.
- **Stability Guarantee:** `/api/v1/` APIs maintain strict backward compatibility. Non-breaking additions (optional fields, new endpoints) may be introduced within v1.
- **Deprecation Policy:** Any breaking change will be introduced under a new version prefix (e.g. `/api/v2/`). Deprecated v1 endpoints will receive a minimum **6-month deprecation period** with warning headers (`Sunset` / `Deprecation`) prior to decommission.

### `ResponceSignal` Legacy Naming
- The enum and response signal `ResponceSignal` uses an intentional legacy spelling (with a `c` instead of `s`).
- **Do not alter or refactor this identifier**: it is intentionally preserved to maintain backward compatibility across existing client SDKs, API integrations, and database logs.


---

## Security & Operations

- **Flower Monitoring Security:** Flower dashboard access is restricted to localhost (`127.0.0.1:5555`) in Docker Compose and requires HTTP Basic Auth credentials via `CELERY_FLOWER_USER` and `CELERY_FLOWER_PASSWORD`.
- **Per-Tenant LLM Quotas:** Users have configurable `monthly_llm_budget` limits tracked automatically via query audit logs to prevent runaway inference expenditures.