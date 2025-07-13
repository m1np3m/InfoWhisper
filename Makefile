.PHONY: all run stop down

all: run

run:
	bash run_all.sh

stop:
	docker-compose -f CDC/rabbitmq/docker-compose.yml down
	docker-compose -f Datacollection_pipeline/docker-compose.yaml down
	docker-compose -f feature_pipeline/docker-compose.yml down
	docker-compose -f langfuse-main/docker-compose.yml down
	docker-compose -f MLflow/docker-compose.yaml down
	@echo "You need to manually stop Python processes (or use pkill if Linux)."

down: stop
