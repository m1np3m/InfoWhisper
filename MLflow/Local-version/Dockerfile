FROM python:3.10-slim


# Cài các thư viện SSL và các dependencies build Python modules
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Sau đó mới chạy pip install
RUN pip install --upgrade pip
RUN pip install mlflow psycopg2-binary
