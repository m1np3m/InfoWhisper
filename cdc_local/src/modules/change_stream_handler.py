from rabbitmq_publisher import RabbitMQPublisher
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChangeStreamHandler:
    def __init__(self, publisher: RabbitMQPublisher):
        self.publisher = publisher

    def process(self, change: dict, collection_name: str):
        op = change['operationType']
        message = {
            'timestamp': datetime.now().isoformat(),
            'operation': op,
            'collection': collection_name
        }

        if op == 'insert':
            message['documentId'] = str(change['fullDocument']['_id'])
            message['document'] = {k: v for k, v in change['fullDocument'].items() if k != '_id'}
        elif op == 'update':
            message['documentId'] = str(change['documentKey']['_id'])
            if 'updateDescription' in change:
                message['updatedFields'] = change['updateDescription'].get('updatedFields', {})
                message['removedFields'] = change['updateDescription'].get('removedFields', [])
        elif op == 'delete':
            message['documentId'] = str(change['documentKey']['_id'])
        elif op == 'replace':
            message['documentId'] = str(change['documentKey']['_id'])
            message['fullDocument'] = change.get('fullDocument', {})

        self.publisher.publish(message)