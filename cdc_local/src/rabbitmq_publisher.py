import os
import json
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQPublisher:
    def __init__(self):
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = os.getenv("RABBITMQ_USER", "VinhThuan")
        self.password = os.getenv("RABBITMQ_PASS", "VinhThuan")
        self.queue = os.getenv("RABBITMQ_QUEUE", "hello")
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            params = pika.ConnectionParameters(
                host=self.host, port=self.port, credentials=credentials,
                heartbeat=600, blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue, durable=True)
            logger.info("Kết nối RabbitMQ thành công.")
        except (AMQPConnectionError, AMQPChannelError) as e:
            logger.error(f"Lỗi kết nối RabbitMQ: {e}")
            raise

    def publish(self, message: dict):
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=json.dumps(message,default=str),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            logger.info(f"Đã gửi message: {message['operation']} - {message['collection']} - {message['documentId']}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi message: {e}")
            raise

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Đã đóng kết nối RabbitMQ")