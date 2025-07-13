import os
import json
import pika
import logging
from dotenv import load_dotenv
from celery import Celery
from pika.exceptions import AMQPConnectionError, AMQPChannelError

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("consumer.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MessageConsumer")

# Load biến môi trường
load_dotenv()

# Cấu hình RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "VinhThuan")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "VinhThuan")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "hello")

# Kết nối Celery - QUAN TRỌNG: Sử dụng cùng tên module với worker
app = Celery('celery_worker')
app.config_from_object('celery_config')

class MessageConsumer:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            params = pika.ConnectionParameters(
                host=RABBITMQ_HOST, 
                port=RABBITMQ_PORT, 
                credentials=credentials,
                heartbeat=600, 
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            logger.info(f"Kết nối RabbitMQ thành công với queue: {RABBITMQ_QUEUE}")
        except (AMQPConnectionError, AMQPChannelError) as e:
            logger.error(f"Lỗi kết nối RabbitMQ: {e}")
            raise

    def callback(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            logger.info(f"Nhận được message: {message['operation']} - {message['collection']} - {message.get('documentId', 'N/A')}")
            
            # Gửi task đến Celery worker - đảm bảo tên task giống với celery_worker.py
            app.send_task('process_mongodb_change', args=[message])
            logger.info(f"Đã gửi task 'process_mongodb_change' đến Celery worker")
            
            # Xác nhận xử lý message thành công
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Lỗi xử lý message: {e}")
            # Từ chối message để xử lý lại sau
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start_consuming(self):
        try:
            # Thiết lập prefetch để không nhận quá nhiều message cùng lúc
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=self.callback
            )
            logger.info(f"Bắt đầu lắng nghe message từ queue {RABBITMQ_QUEUE}...")
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Dừng tiêu thụ message do người dùng yêu cầu.")
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Lỗi trong quá trình tiêu thụ message: {e}")
        finally:
            self.close()

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Đã đóng kết nối RabbitMQ")

def main():
    consumer = MessageConsumer()
    try:
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Lỗi không xác định: {e}")
        consumer.close()

if __name__ == "__main__":
    main()