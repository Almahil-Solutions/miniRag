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
1) Create a .env file in the root directory:
```bash
cp .env.EXAMPLE .env
```
2) Set your values in the `.env` file. like `API_KEY` value.

### Setup docker
1) Create a .env file in the docker directory:
```bash
cp .env.EXAMPLE .env
```
2) Set your values in the `.env` file. like `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` values.
3) Run the docker container:
```bash
docker-compose up -d
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


open your browser and go to `http://localhost:5555` to see the dashboard.