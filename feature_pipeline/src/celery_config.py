import os
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

# Cấu hình RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "VinhThuan")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "VinhThuan")

# Cấu hình Celery broker
broker_url = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"

# Thêm các task mặc định
task_routes = {
    'process_mongodb_change': {'queue': 'default'}
}

# Cấu hình worker
worker_prefetch_multiplier = 1
task_acks_late = True
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
enable_utc = True