import os
import sys
import time
import json
import logging
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError
from dotenv import load_dotenv
from rabbitmq_publisher import RabbitMQPublisher
from change_stream_handler import ChangeStreamHandler

# Fix encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mongo_watch.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MongoWatcher")

class MongoWatcher:
    def __init__(self, handler: ChangeStreamHandler):
        self.mongo_uri = os.getenv("MONGO_URI")
        self.db_name = os.getenv("MONGO_DB_NAME")
        self.collections = os.getenv("COLLECTIONS", "chinh-tri,cong-nghe,doi-song,giao-duc,phap-luat,the-gioi").split(",")
        self.handler = handler
        self.client = None

    def connect(self):
        try:
            self.client = MongoClient(self.mongo_uri)
            self.client.admin.command('ping')
            logger.info("Kết nối MongoDB thành công.")
        except PyMongoError as e:
            logger.error(f"Lỗi kết nối MongoDB: {e}")
            raise

    def watch(self):
        try:
            self.connect()
            db = self.client[self.db_name]
            change_streams = []

            for col_name in self.collections:
                collection = db[col_name]
                logger.info(f"Theo dõi collection: {col_name}")
                pipeline = [{'$match': {'operationType': {'$in': ['insert', 'update', 'delete']}}}]
                stream = collection.watch(pipeline=pipeline, full_document='updateLookup')
                change_streams.append((stream, col_name))

            while True:
                for stream, name in change_streams:
                    if stream.alive:
                        change = stream.try_next()
                        if change:
                            self.handler.process(change, name)
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Dừng theo dõi do người dùng yêu cầu.")
        except Exception as e:
            logger.error(f"Lỗi: {e}")
        finally:
            self.close()

    def close(self):
        if self.client:
            self.client.close()
            logger.info("Đã đóng kết nối MongoDB.")

def main():
    logger.info("Khởi động hệ thống theo dõi MongoDB...")
    publisher = RabbitMQPublisher()
    handler = ChangeStreamHandler(publisher)
    watcher = MongoWatcher(handler)

    try:
        watcher.watch()
    finally:
        publisher.close()

if __name__ == "__main__":
    main()
