import os
import uuid
from typing import Optional, Callable

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.frame import Method
from pika.spec import Queue

from djing2.lib.logger import logger


class PikaClient:
    publish_queue_name: str
    connection: pika.BlockingConnection
    channel: BlockingChannel
    publish_queue: Method[Queue.DeclareOk]
    callback_queue: Optional[str]
    process_callable: Callable

    def __init__(self, process_callable: Callable):
        self.publish_queue_name = os.getenv('PUBLISH_QUEUE', 'foo_publish_queue')
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.getenv('RABBIT_HOST', '127.0.0.1'))
        )
        self.channel = self.connection.channel()
        self.publish_queue = self.channel.queue_declare(queue=self.publish_queue_name)
        self.callback_queue = self.publish_queue.method.queue
        # self.response = None
        self.process_callable = process_callable
        logger.info('Pika connection initialized')

    async def consume(self, loop):
        """Setup message listener with the current running loop"""
        connection = await connect_robust(
            host=os.getenv('RABBIT_HOST', '127.0.0.1'),
            port=5672,
            loop=loop
        )
        channel = await connection.channel()
        queue = await channel.declare_queue(os.getenv('CONSUME_QUEUE', 'foo_consume_queue'))
        r = queue.consume(self.process_incoming_message, no_ack=False)
        # logger.info('Established pika async listener')
        return r

    async def process_incoming_message(self, message):
        """Processing incoming message from RabbitMQ"""
        message.ack()
        body = message.body
        logger.info('Received message')
        if body:
            self.process_callable(json.loads(body))

    def send_message(self, message: dict):
        """Method to publish message to RabbitMQ"""
        self.channel.basic_publish(
            exchange='',
            routing_key=self.publish_queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=str(uuid.uuid4())
            ),
            body=json.dumps(message)
        )
