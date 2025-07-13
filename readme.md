# InfoWhisper

**InfoWhisper** is a modular, end-to-end AI pipeline designed for real-time news processing and analysis using LLMs (Large Language Models). The system supports data ingestion, feature extraction, inference, and monitoring components, with integrations for Langfuse and MLflow to provide full observability and traceability.

## Project Structure

```
InfoWhisper/
├── CDC/                        # Change Data Capture with MongoDB and RabbitMQ
├── Database-VectorDatabase/   # Database
├── Datacollection_pipeline/   # Data ingestion using Apache Airflow
├── feature_pipeline/          # Feature engineering via Celery workers
├── Inference_pipeline/        # News inference and UI modules
├── langfuse-main/             # Langfuse monitoring for LLMs
├── MLflow/                    # Experiment tracking with MLflow
├── notebook/                  # Jupyter notebooks for potential RAG pipeline, evaluation, and indexing
├── run_all.sh                 # Shell script to launch the full pipeline
├── Makefile                   # CLI-style task shortcuts
```

## Installation

**Quick start:**

```bash
git clone https://github.com/m1np3m/InfoWhisper.git
cd InfoWhisper
bash run_all.sh
```

Alternatively, launch components individually via `make`:

```bash
make cdc             # Start CDC with MongoDB and RabbitMQ
make data_pipeline   # Launch data ingestion (Airflow)
make feature         # Start feature extraction workers
make inference       # Launch inference web interface
make mlflow          # Start MLflow tracking server
make langfuse        # Start Langfuse observability stack
```

## Module Overview

### 1. `CDC/`
- Listens for document changes in MongoDB
- Sends change events to RabbitMQ
- Main file: `src/Mongo_CDC.py`

### 2. `Database-VectorDatabase/`
- MongoDB and Qdrants

### 3. `Datacollection_pipeline/`
- DAGs powered by Apache Airflow to crawl and schedule news scraping tasks
- Sample DAGs include:
  - `deepai_crawler_10min`

### 4. `feature_pipeline/`
- Asynchronous Celery pipeline to extract features from raw text
- Includes chunking, embedding generation, and storage

### 5. `Inference_pipeline/`
- Multiple frontend options for viewing processed news:
  - `Streamlit_ver/`: LLM-powered summarization and display
  - `News_web/`: Standard web interface
  - `Error_handling_UI/`: Custom UI for failure/retry handling

### 6. `MLflow/`
- Local and remote tracking setup for training runs
- View experiment metrics, parameters, and artifacts

### 7. `langfuse-main/`
- Real-time tracing and analysis of LLM requests
- Includes dashboards, workers, and backend services

### 8. `notebook/`
- Includes RAG (Retrieval-Augmented Generation) experiments
- Summary evaluation using FactScore and QA-based metrics

## Monitoring and Observability

| Tool        | Purpose                           |
|-------------|------------------------------------|
| MLflow      | Experiment tracking                |
| Langfuse    | LLM observability and tracing      |
| Airflow UI  | Workflow orchestration and logging |

## Dependencies

Each module includes its own `requirements.txt` and `Dockerfile`. Core dependencies include:

- `langchain`, `transformers`, `sentence-transformers`
- `pymongo`, `playwright`, `celery`, `streamlit`
- `mlflow`, `langfuse`, `airflow`

## Configuration

Environment variables are defined per module using `.env` files. Make sure to configure them appropriately before running each component.
