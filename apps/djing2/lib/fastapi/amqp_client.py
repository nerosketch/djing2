from typing import Optional
import asyncio
import json

from aio_pika import connect, Message
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractConnection, AbstractIncomingMessage
from django.conf import settings

GENERAL_AMQP_HOST = getattr(settings, 'GENERAL_AMQP_HOST', 'localhost')

# TODO: make gently closing connection


class AmqpProxyClient:
    channel: Optional[AbstractChannel] = None
    queue: Optional[AbstractQueue] = None
    connection: Optional[AbstractConnection] = None

    async def a_init(self):
        # Perform connection
        url = f"amqp://user:passw@{GENERAL_AMQP_HOST}/"

        print('Connecting to: %s' % url)
        connection = await connect(url)
        self.connection = connection

        channel = await connection.channel()
        self.channel = channel

        print('Established amqp async listener')
        return asyncio.Future()

    async def _declate_queue(self):
        # Declaring queue
        queue = await self.channel.declare_queue("hello")
        self.queue = queue
        return queue

    async def consume(self):
        """Setup message listener with the current running loop"""
        print('Pre Start consume')

        queue = await self._declate_queue()

        print('Start consume')
        await queue.consume(self.process_incoming_message)
        print('consume return Future')
        return asyncio.Future()

    def process_incoming_message(self, message: AbstractIncomingMessage):
        """Processing incoming message from RabbitMQ"""
        body = message.body
        print('Received message: %s' % str(body))

    async def send_message(self, msg: dict, **json_kwargs):
        """Method to publish message to RabbitMQ"""
        # Sending the message
        await self.channel.default_exchange.publish(
            Message(
                body=json.dumps(msg, **json_kwargs).encode()
            ),
            routing_key=self.queue.name,
        )

    def __del__(self):
        if self.connection:
            print('Close connection')
            asyncio.create_task(
                self.connection.close()
            )
            print('Connection closed')
