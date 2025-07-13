.PHONY: all run stop down \
        cdc data_pipeline feature inference mlflow langfuse \
        stop_cdc stop_data stop_feature stop_inference stop_mlflow stop_langfuse

all: run

run:
	bash run_all.sh

# --- Individual RUN targets ---
database:
	docker-compose -f Database-VectorDatabase/docker-compose.yml up -d
cdc:
	docker-compose -f CDC/rabbitmq/docker-compose.yml up -d

data_pipeline:
	docker-compose -f Datacollection_pipeline/docker-compose.yaml up -d

feature:
	docker-compose -f feature_pipeline/docker-compose.yml up -d

inference:
	docker-compose -f Inference_pipeline/docker-compose.yml up -d

mlflow:
	docker-compose -f MLflow/docker-compose.yaml up -d

langfuse:
	docker-compose -f langfuse-main/docker-compose.yml up -d

# --- Individual STOP targets ---
stop_cdc:
	docker-compose -f CDC/rabbitmq/docker-compose.yml down

stop_data:
	docker-compose -f Datacollection_pipeline/docker-compose.yaml down

stop_feature:
	docker-compose -f feature_pipeline/docker-compose.yml down

stop_inference:
	docker-compose -f Inference_pipeline/docker-compose.yml down

stop_mlflow:
	docker-compose -f MLflow/docker-compose.yaml down

stop_langfuse:
	docker-compose -f langfuse-main/docker-compose.yml down

# Stop all
stop: stop_cdc stop_data stop_feature stop_inference stop_mlflow stop_langfuse
	@echo "Note: You may still need to manually kill Python background processes."

down: stop
