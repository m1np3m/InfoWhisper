#!/bin/bash

# CDC RabbitMQ
echo "Starting RabbitMQ CDC..."
docker-compose -f CDC/rabbitmq/docker-compose.yml up -d

# MongoDB CDC
echo "Running MongoDB CDC script..."
python3 CDC/src/Mongo_CDC.py &

# Data Collection Pipeline
echo "Starting Data Collection Pipeline..."
docker-compose -f Datacollection_pipeline/docker-compose.yaml up -d

# Inference Pipelines
echo "Running News inference..."
python3 Inference_pipeline/News_web/News.py &

echo "Running Streamlit UI..."
python3 Inference_pipeline/Streamlit_ver/UI.py &

# Langfuse
echo "Starting Langfuse..."
docker-compose -f langfuse-main/docker-compose.yml up -d

# MLflow
echo "Starting MLflow..."
docker-compose -f MLflow/docker-compose.yaml up -d

echo "All services are running."
